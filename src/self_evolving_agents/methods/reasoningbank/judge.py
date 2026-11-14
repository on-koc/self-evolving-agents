"""The LLM-as-a-judge of ReasoningBank: a success or failure label without ground truth."""

from __future__ import annotations

import re
from typing import Any

from ...envs.base import EnvSpec
from ...llm import LLMRequest, user
from ...types import Trajectory
from ..stream import Verdict
from . import prompts
from .render import final_state, render_actions, render_trajectory

_STATUS = re.compile(r"Status\s*:\s*[\"'`*]*\s*(success|failure)", re.IGNORECASE)
_THOUGHTS = re.compile(r"Thoughts\s*:\s*(.*?)(?=\n\s*Status\s*:|\Z)", re.IGNORECASE | re.DOTALL)

HISTORIES = ("actions", "steps")


class LLMJudge:
    """Labels an episode success or failure (paper section 3.2, Figure 10).

    The judge is given the task, the agent's action history and the final state. An
    unparseable reply counts as failure, as in the reference code, where anything
    other than a "success" status is a failure.

    Args:
        temperature: 0.0 in the paper. Backends whose models accept no temperature
            ignore it.
        strict: add the strictness rules the reference code introduced after
            publication. Off by default.
        history: ``"actions"`` shows the judge the action history, as published.
            ``"steps"`` shows reasoning, observation summaries and feedback as well;
            that is more than the published judge sees.
    """

    source = "llm"

    def __init__(
        self,
        llm: Any,
        *,
        temperature: float | None = 0.0,
        strict: bool = False,
        history: str = "actions",
        max_tokens: int = 16000,
    ):
        if history not in HISTORIES:
            raise ValueError(f"history must be one of {HISTORIES}")
        self.llm = llm
        self.temperature = temperature
        self.strict = strict
        self.history = history
        self.max_tokens = max_tokens

    def judge(self, spec: EnvSpec, query: str, traj: Trajectory) -> Verdict:
        history = (
            render_actions(traj)
            if self.history == "actions"
            else render_trajectory(traj, observations=True)
        )
        response = self.llm.complete(
            LLMRequest(
                system=prompts.judge_system(spec.domain, spec.success_doc, self.strict),
                messages=[user(prompts.judge_input(query, history, final_state(traj)))],
                purpose="judge",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
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
