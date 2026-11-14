"""ReasoningBank as a memory method: retrieve, then judge, extract and consolidate.

This is the closed loop of the paper's section 3.2, expressed as a
:class:`~self_evolving_agents.methods.stream.Memory` so that the shared stream loop
can run it. Every default in :class:`ReasoningBankConfig` is the published value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ...embeddings import Embedder
from ...envs.base import TextEnv
from ...provenance import WAS_DERIVED_FROM, WAS_GENERATED_BY, ProvenanceStore
from ...types import Task, Trajectory
from ..stream import EnvJudge, Judge, Learned, Memory, Retrieval, Verdict
from . import prompts
from .bank import ReasoningBank, Retrieved
from .extraction import MemoryExtractor
from .judge import LLMJudge
from .render import memory_block
from .schema import Experience, MemoryItem

JUDGES = ("llm", "env")


@dataclass
class ReasoningBankConfig:
    """Parameters of the baseline. Defaults are the paper's; the comments say where from."""

    #: Experiences retrieved per task: the paper's top-k (Appendix A.2; k = 1 was best
    #: in Appendix C.1).
    retrieve_k: int = 1
    #: Items extracted per trajectory at most (Appendix A.2).
    max_items: int = 3
    #: Learn from failed trajectories too. ``False`` is the paper's success-only ablation.
    include_failures: bool = True
    #: ``"llm"``: LLM-as-a-judge without ground truth (the method). ``"env"``: the
    #: simulator's criterion, a control that removes judge error.
    judge: str = "llm"
    #: Decoding temperatures (Appendices A.2 and B.1). Ignored by backends whose
    #: models accept none.
    judge_temperature: float | None = 0.0
    extraction_temperature: float | None = 1.0
    #: Which experience wins an exact tie in similarity (reference code: the oldest).
    tie_break: str = "oldest"

    # The remaining switches reproduce details of the reference code that are not in
    # the paper. All are off by default.
    #: Inject items with their description as well as title and content.
    inject_description: bool = False
    #: Append the judge's reasoning to the extractor's input.
    extractor_sees_judge_rationale: bool = False
    #: Use the extraction prompts as revised in the reference code after publication.
    revised_prompts: bool = False
    #: Add the reference code's strictness rules to the judge.
    judge_strict: bool = False
    #: Embed ``"Instruct: ...\\nQuery: ..."`` for the lookup, with this instruction.
    query_instruction: str | None = None

    def __post_init__(self) -> None:
        if self.judge not in JUDGES:
            raise ValueError(f"judge must be one of {JUDGES}")
        if self.retrieve_k < 0 or self.max_items < 1:
            raise ValueError("retrieve_k must be non-negative and max_items at least 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReasoningBankMemory(Memory):
    """Retrieval from, and consolidation into, a :class:`ReasoningBank`.

    Args:
        bank: the store.
        extractor: distils items from judged trajectories.
        k: number of experiences whose items are retrieved.
        include_failures: whether failed trajectories are learned from.
        inject_description: see :class:`ReasoningBankConfig`.
        instruction: text placed before the retrieved items in the system prompt.
        store: provenance store for experiences, items and their links.
    """

    name = "reasoningbank"
    learns = True

    def __init__(
        self,
        bank: ReasoningBank,
        extractor: MemoryExtractor,
        *,
        k: int = 1,
        include_failures: bool = True,
        inject_description: bool = False,
        instruction: str = prompts.MEMORY_INSTRUCTION,
        store: ProvenanceStore | None = None,
    ):
        self.bank = bank
        self.extractor = extractor
        self.k = k
        self.include_failures = include_failures
        self.inject_description = inject_description
        self.instruction = instruction
        self.store = store

    # ------------------------------------------------------------------ retrieval

    def retrieve_items(self, env: TextEnv, task: Task, query: str) -> list[Retrieved]:
        return self.bank.retrieve(query, k=self.k)

    def render(self, items: list[MemoryItem]) -> Any:
        return memory_block(
            items, instruction=self.instruction, with_description=self.inject_description
        )

    def retrieve(self, env: TextEnv, task: Task, query: str) -> Retrieval:
        retrieved = self.retrieve_items(env, task, query)
        return Retrieval(
            block=self.render([r.item for r in retrieved]),
            details=[
                {"item": r.item.id, "experience": r.experience_id, "score": round(r.score, 4)}
                for r in retrieved
            ],
        )

    # ------------------------------------------------------------------ learning

    def consolidate(
        self,
        task: Task,
        query: str,
        trajs: list[Trajectory],
        items: list[MemoryItem],
        call_id: str,
        verdict_label: str,
        meta: dict[str, Any],
    ) -> Experience:
        """Append one experience to the bank and record where it came from."""
        experience = self.bank.add(
            Experience(
                query=query,
                items=items,
                task_key=task.key,
                task=task.to_dict(),
                trajectory_ids=[t.id for t in trajs],
                verdict=verdict_label,
                meta=meta,
            )
        )
        if self.store is not None:
            header = experience.to_dict()
            header.pop("items")
            self.store.add_node(experience.id, "experience", label=task.key, data=header)
            for traj in trajs:
                self.store.link(experience.id, WAS_DERIVED_FROM, traj.id)
            for item in experience.items:
                self.store.add_node(item.id, "memory_item", label=item.title, data=item.to_dict())
                self.store.link(item.id, WAS_DERIVED_FROM, experience.id)
                for traj in trajs:
                    self.store.link(item.id, WAS_DERIVED_FROM, traj.id)
                if call_id:
                    self.store.link(item.id, WAS_GENERATED_BY, call_id)
        return experience

    def learns_from(self, verdict: Verdict) -> bool:
        return verdict.success or self.include_failures

    def learn_single(
        self, env: TextEnv, task: Task, query: str, traj: Trajectory, verdict: Verdict
    ) -> Learned:
        if not self.learns_from(verdict):
            return Learned()
        items, call_id = self.extractor.extract(env.spec, query, traj, verdict)
        experience = self.consolidate(
            task, query, [traj], items, call_id, verdict.label, {"judge": verdict.to_dict()}
        )
        return Learned([i.id for i in experience.items], [experience.id])

    def stats(self) -> dict[str, Any]:
        return self.bank.stats()


def build(
    config: ReasoningBankConfig,
    llm: Any,
    *,
    bank_path: str | Path | None = None,
    embedder: Embedder | None = None,
    store: ProvenanceStore | None = None,
    instruction: str = prompts.MEMORY_INSTRUCTION,
) -> tuple[ReasoningBankMemory, Judge]:
    """The baseline's memory and judge, wired as the configuration says."""
    bank = ReasoningBank(
        bank_path,
        embedder,
        query_instruction=config.query_instruction,
        tie_break=config.tie_break,
    )
    extractor = MemoryExtractor(
        llm,
        max_items=config.max_items,
        temperature=config.extraction_temperature,
        revised=config.revised_prompts,
        judge_rationale=config.extractor_sees_judge_rationale,
    )
    memory = ReasoningBankMemory(
        bank,
        extractor,
        k=config.retrieve_k,
        include_failures=config.include_failures,
        inject_description=config.inject_description,
        instruction=instruction,
        store=store,
    )
    return memory, make_judge(config, llm)


def make_judge(config: ReasoningBankConfig, llm: Any) -> Judge:
    if config.judge == "env":
        return EnvJudge()
    return LLMJudge(llm, temperature=config.judge_temperature, strict=config.judge_strict)
