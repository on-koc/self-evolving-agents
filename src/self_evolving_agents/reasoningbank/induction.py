"""Judging episodes and distilling memory items from them."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from ..envs.base import EnvSpec
from ..llm import LLMRequest, user
from ..types import Trajectory
from . import prompts
from .render import render_for_extraction, render_many, render_trajectory
from .schema import (
    SOURCE_CONTRAST,
    SOURCE_FAILURE,
    SOURCE_REFINE,
    SOURCE_SUCCESS,
    MemoryItem,
    Verdict,
    parse_memory_items,
)

_STATUS = re.compile(r"Status\s*:\s*[\"'`*]*\s*(success|failure)", re.IGNORECASE)
_THOUGHTS = re.compile(r"Thoughts\s*:\s*(.*?)(?=\n\s*Status\s*:|\Z)", re.IGNORECASE | re.DOTALL)
_BEST = re.compile(r"Best\s*:\s*[\"'`*#]*\s*(?:trajectory\s*)?(\d+)", re.IGNORECASE)


class EnvJudge:
    """Uses the simulator's own success criterion.

    This is the reference code's ``--criteria gt`` setting. It is the right choice
    when the environment really does tell the agent whether it succeeded, and an
    upper bound on judge quality otherwise.
    """

    source = "env"

    def judge(self, spec: EnvSpec, query: str, traj: Trajectory, **_: Any) -> Verdict:
        outcome = traj.outcome
        if outcome is None or outcome.success is None:
            raise ValueError("the environment reported no success criterion for this episode")
        reason = (
            "ground-truth criterion met" if outcome.success else "ground-truth criterion not met"
        )
        if outcome.failure:
            reason += f" (failure mode: {outcome.failure})"
        return Verdict(success=bool(outcome.success), thoughts=reason, source="env")


class LLMJudge:
    """LLM-as-a-judge: labels an episode success or failure without ground truth.

    The judge sees what the agent saw. An unparseable reply counts as failure, in
    line with the prompt's rule that uncertainty resolves to failure.
    """

    source = "llm"

    def __init__(self, llm: Any, *, max_tokens: int = 16000):
        self.llm = llm
        self.max_tokens = max_tokens

    def judge(
        self,
        spec: EnvSpec,
        query: str,
        traj: Trajectory,
        reference: str = "",
        **_: Any,
    ) -> Verdict:
        prompt = (
            f"Task: {query}\n\n"
            f"Rules of the environment:\n{spec.rules_doc}\n\n"
            f"Trajectory:\n{render_trajectory(traj)}\n\n"
            f"Final state:\n{traj.final_observation or '(not available)'}"
        )
        if reference:
            prompt += f"\n\nFor calibration: {reference}"
        response = self.llm.complete(
            LLMRequest(
                system=prompts.judge_system(spec.domain, spec.success_doc),
                messages=[user(prompt)],
                purpose="judge",
                max_tokens=self.max_tokens,
                temperature=0.0,
                meta={"trajectory": traj.id},
            )
        )
        status = _STATUS.findall(response.text)
        thoughts_match = _THOUGHTS.search(response.text)
        thoughts = " ".join((thoughts_match.group(1) if thoughts_match else response.text).split())
        if not status:
            return Verdict(
                success=False,
                thoughts=f"[judge reply had no parsable status; counted as failure] {thoughts[:500]}",
                source="llm",
                llm_call_id=response.call_id,
            )
        return Verdict(
            success=status[-1].lower() == "success",
            thoughts=thoughts,
            source="llm",
            llm_call_id=response.call_id,
        )


class MemoryExtractor:
    """Distils memory items from trajectories with the ReasoningBank prompts."""

    def __init__(
        self,
        llm: Any,
        *,
        max_items: int = 3,
        max_items_contrast: int = 5,
        max_tokens: int = 16000,
    ):
        self.llm = llm
        self.max_items = max_items
        self.max_items_contrast = max_items_contrast
        self.max_tokens = max_tokens

    def _call(self, system: str, prompt: str, source: str, limit: int, meta: dict[str, Any]):
        response = self.llm.complete(
            LLMRequest(
                system=system,
                messages=[user(prompt)],
                purpose="extract",
                max_tokens=self.max_tokens,
                temperature=1.0,
                meta=meta,
            )
        )
        return parse_memory_items(response.text, source=source, limit=limit), response.call_id

    def extract(
        self, spec: EnvSpec, query: str, traj: Trajectory, verdict: Verdict
    ) -> tuple[list[MemoryItem], str]:
        """Items from one trajectory, using the success or the failure prompt."""
        if verdict.success:
            system = prompts.success_extraction_system(spec.domain, self.max_items)
            source = SOURCE_SUCCESS
        else:
            system = prompts.failure_extraction_system(spec.domain, self.max_items)
            source = SOURCE_FAILURE
        prompt = render_for_extraction(query, traj, verdict.thoughts, verdict.label)
        return self._call(system, prompt, source, self.max_items, {"trajectory": traj.id})

    def extract_contrast(
        self, spec: EnvSpec, query: str, trajs: Sequence[Trajectory]
    ) -> tuple[list[MemoryItem], str]:
        """Self-contrast across several attempts at the same task (MaTTS parallel)."""
        system = prompts.contrast_extraction_system(spec.domain, self.max_items_contrast)
        prompt = render_many(query, trajs)
        return self._call(
            system,
            prompt,
            SOURCE_CONTRAST,
            self.max_items_contrast,
            {"trajectories": [t.id for t in trajs]},
        )

    def extract_refine(
        self, spec: EnvSpec, query: str, trajs: Sequence[Trajectory], notes: Sequence[str]
    ) -> tuple[list[MemoryItem], str]:
        """Items from a series of attempts and the notes written between them (MaTTS sequential)."""
        system = prompts.refine_extraction_system(spec.domain, self.max_items)
        parts = [render_many(query, trajs)]
        for i, note in enumerate(notes, 1):
            parts.append(f"**Notes written after attempt {i}:**\n{note}")
        return self._call(
            system,
            "\n\n".join(parts),
            SOURCE_REFINE,
            self.max_items,
            {"trajectories": [t.id for t in trajs]},
        )


def refine_notes(
    llm: Any,
    spec: EnvSpec,
    query: str,
    trajs: Sequence[Trajectory],
    previous_notes: Sequence[str],
    *,
    max_tokens: int = 16000,
) -> tuple[str, str]:
    """Self-refinement: re-examine the attempts so far and write notes for the next one."""
    system = (
        f"You are an agent working on {spec.domain}.\n\n{spec.instructions()}\n\n## Task\n{query}"
    )
    body = render_many(query, trajs)
    for i, note in enumerate(previous_notes, 1):
        body += f"\n\n**Your notes after attempt {i}:**\n{note}"
    check = prompts.SEQUENTIAL_CHECK if not previous_notes else prompts.SEQUENTIAL_CHECK_FOLLOWING
    response = llm.complete(
        LLMRequest(
            system=system,
            messages=[user(body + "\n\n" + check)],
            purpose="refine",
            max_tokens=max_tokens,
            meta={"trajectories": [t.id for t in trajs]},
        )
    )
    return response.text.strip(), response.call_id


def select_best(
    llm: Any,
    spec: EnvSpec,
    query: str,
    trajs: Sequence[Trajectory],
    *,
    max_tokens: int = 16000,
) -> tuple[int, str, str]:
    """Best-of-N: ask the model which attempt was best. Returns ``(index, thoughts, call_id)``.

    Falls back to the first attempt when the reply names no valid trajectory.
    """
    if len(trajs) == 1:
        return 0, "only one attempt", ""
    response = llm.complete(
        LLMRequest(
            system=prompts.selection_system(spec.domain, len(trajs)),
            messages=[user(render_many(query, trajs))],
            purpose="select",
            max_tokens=max_tokens,
            temperature=0.0,
            meta={"trajectories": [t.id for t in trajs]},
        )
    )
    picks = [int(m) for m in _BEST.findall(response.text)]
    index = picks[-1] - 1 if picks and 1 <= picks[-1] <= len(trajs) else 0
    return index, " ".join(response.text.split())[:1000], response.call_id
