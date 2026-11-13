"""Memory extraction of ReasoningBank: distilling items from a judged trajectory."""

from __future__ import annotations

from typing import Any

from ...envs.base import EnvSpec
from ...llm import LLMRequest, user
from ...types import Trajectory
from ..stream import Verdict
from . import prompts
from .render import render_trajectory
from .schema import SOURCE_FAILURE, SOURCE_SUCCESS, MemoryItem, parse_memory_items


class MemoryExtractor:
    """Turns one trajectory into at most ``max_items`` memory items (paper, Appendix A).

    A trajectory judged successful is distilled with the success instruction, one
    judged failed with the failure instruction (Figure 9). The extractor is given the
    query and the agent's reasoning and action at each step.

    Args:
        max_items: 3 in the paper.
        temperature: 1.0 in the paper. Ignored by backends that accept none.
        revised: use the reference code's later wording of the prompts.
        observations: also show each step's observation summary and feedback. Not
            part of the published method.
        judge_rationale: append the judge's reasoning to the input, as the reference
            code does. Not in the paper.
    """

    def __init__(
        self,
        llm: Any,
        *,
        max_items: int = 3,
        temperature: float | None = 1.0,
        revised: bool = False,
        observations: bool = False,
        judge_rationale: bool = False,
        max_tokens: int = 16000,
    ):
        self.llm = llm
        self.max_items = max_items
        self.temperature = temperature
        self.revised = revised
        self.observations = observations
        self.judge_rationale = judge_rationale
        self.max_tokens = max_tokens

    # Methods built on top override these two.

    def system_prompt(self, spec: EnvSpec, success: bool) -> str:
        build = prompts.success_extraction_system if success else prompts.failure_extraction_system
        return build(spec.domain, self.max_items, self.revised)

    def user_prompt(self, query: str, traj: Trajectory, verdict: Verdict) -> str:
        text = prompts.extraction_input(
            query, render_trajectory(traj, observations=self.observations)
        )
        if self.judge_rationale and verdict.thoughts:
            outcome = "succeeded" if verdict.success else "failed"
            text += f"\n\nThe task {outcome} because: {verdict.thoughts}"
        return text

    def complete(
        self, system: str, prompt: str, source: str, limit: int, meta: dict[str, Any]
    ) -> tuple[list[MemoryItem], str]:
        response = self.llm.complete(
            LLMRequest(
                system=system,
                messages=[user(prompt)],
                purpose="extract",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                meta=meta,
            )
        )
        return parse_memory_items(response.text, source=source, limit=limit), response.call_id

    def extract(
        self, spec: EnvSpec, query: str, traj: Trajectory, verdict: Verdict
    ) -> tuple[list[MemoryItem], str]:
        """Items from one trajectory, and the id of the model call that produced them."""
        return self.complete(
            self.system_prompt(spec, verdict.success),
            self.user_prompt(query, traj, verdict),
            SOURCE_SUCCESS if verdict.success else SOURCE_FAILURE,
            self.max_items,
            {"trajectory": traj.id},
        )
