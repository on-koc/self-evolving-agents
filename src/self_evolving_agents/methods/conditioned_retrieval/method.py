"""Condition-aware ReasoningBank: the retrieval and extraction adaptation as a memory method."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...embeddings import Embedder
from ...envs.base import EnvSpec, TextEnv
from ...provenance import ProvenanceStore
from ...types import Task, Trajectory
from ..reasoningbank import prompts as published
from ..reasoningbank.bank import Retrieved
from ..reasoningbank.extraction import MemoryExtractor
from ..reasoningbank.method import ReasoningBankConfig, ReasoningBankMemory, make_judge
from ..stream import Judge, Retrieval, Verdict
from .bank import MODES, ConditionedBank

# The two instructions this method adds to the published extraction prompts.
CONDITION_NOTES = (
    "  - A rule that works under one configuration can fail under another. In the description, "
    "state the conditions under which the insight was observed, using the conditions given in "
    "the task, and when it should NOT be applied.\n"
    "  - Report quantities you saw in the trajectory as observations. When you explain *why* "
    "something worked or failed, mark the explanation as a hypothesis unless the trajectory "
    "itself demonstrates it."
)


@dataclass
class ConditionedConfig(ReasoningBankConfig):
    """The baseline's parameters plus those of the adaptation.

    The adaptation's defaults are reasoned choices that have not been tuned or
    evaluated; every one of them can be switched back to the baseline's behaviour.
    """

    #: ``"item"`` ranks single items; ``"experience"`` ranks whole experiences.
    retrieval_mode: str = "item"
    #: Cap on retrieved items.
    max_retrieved: int = 6
    #: Share of the relevance given to similarity of operating conditions (0 disables).
    condition_weight: float = 0.5
    #: Bonus for items whose past uses scored well (0 disables).
    utility_weight: float = 0.0
    #: Penalty for returning similar items together (0 disables).
    diversity: float = 0.3
    #: Drop new items at least this similar to an existing one (``None`` disables).
    dedup_threshold: float | None = None
    #: Ask the extractor to state conditions and to mark explanations as hypotheses.
    condition_notes: bool = True
    #: Show the extractor observation summaries and feedback besides reasoning and action.
    observations: bool = True
    #: The newest experience wins ties: in a stream of repeated tasks ties are the
    #: normal case and the oldest experience is rarely the best one to keep returning.
    tie_break: str = "newest"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.retrieval_mode not in MODES:
            raise ValueError(f"retrieval_mode must be one of {MODES}")


class ConditionedExtractor(MemoryExtractor):
    """The published extractor with the two added instructions."""

    def __init__(self, llm: Any, *, condition_notes: bool = True, **kwargs: Any):
        super().__init__(llm, **kwargs)
        self.condition_notes = condition_notes

    def system_prompt(self, spec: EnvSpec, success: bool) -> str:
        text = super().system_prompt(spec, success)
        if not self.condition_notes:
            return text
        marker = "\n\n## Output Format"
        head, tail = text.split(marker, 1)
        return f"{head}\n{CONDITION_NOTES}{marker}{tail}"


class ConditionedMemory(ReasoningBankMemory):
    """ReasoningBank with condition-aware retrieval."""

    name = "conditioned_retrieval"

    def __init__(self, bank: ConditionedBank, extractor: MemoryExtractor, **kwargs: Any):
        self.retrieval = {
            key: kwargs.pop(key)
            for key in ("mode", "max_items", "condition_weight", "utility_weight", "diversity")
        }
        super().__init__(bank, extractor, **kwargs)
        self.bank: ConditionedBank = bank

    def retrieve_items(self, env: TextEnv, task: Task, query: str) -> list[Retrieved]:
        return self.bank.retrieve_conditioned(
            query, k=self.k, conditions=task.conditions, **self.retrieval
        )

    def record_use(self, retrieval: Retrieval, traj: Trajectory, verdict: Verdict | None) -> None:
        # Usage statistics rely only on what the agent itself can observe: the reward
        # it received and the judged outcome.
        self.bank.record_outcome(
            retrieval.block.item_ids, traj.total_reward, verdict.success if verdict else None
        )


def build(
    config: ConditionedConfig,
    llm: Any,
    *,
    bank_path: str | Path | None = None,
    embedder: Embedder | None = None,
    store: ProvenanceStore | None = None,
    instruction: str = published.MEMORY_INSTRUCTION,
) -> tuple[ConditionedMemory, Judge]:
    bank = ConditionedBank(
        bank_path, embedder, dedup_threshold=config.dedup_threshold, tie_break=config.tie_break
    )
    extractor = ConditionedExtractor(
        llm,
        condition_notes=config.condition_notes,
        max_items=config.max_items,
        temperature=config.extraction_temperature,
        revised=config.revised_prompts,
        observations=config.observations,
        judge_rationale=config.extractor_sees_judge_rationale,
    )
    memory = ConditionedMemory(
        bank,
        extractor,
        k=config.retrieve_k,
        include_failures=config.include_failures,
        inject_description=config.inject_description,
        instruction=instruction,
        store=store,
        mode=config.retrieval_mode,
        max_items=config.max_retrieved,
        condition_weight=config.condition_weight,
        utility_weight=config.utility_weight,
        diversity=config.diversity,
    )
    return memory, make_judge(config, llm)
