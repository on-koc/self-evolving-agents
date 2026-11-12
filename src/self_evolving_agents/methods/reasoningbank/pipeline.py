"""The closed loop: retrieve -> act -> judge -> extract -> consolidate.

Tasks arrive as a stream and are handled one at a time, as in the paper's
test-time-learning setting: no ground truth is used to build memory unless the
environment judge is explicitly selected.

Test-time scaling variants:

* ``parallel``  (MaTTS)   k attempts at the same task, one self-contrast extraction
  over all of them, best attempt chosen by the model.
* ``sequential`` (MaTTS)  attempt, re-examine, write notes, attempt again; k attempts
  in total, one extraction over the whole series.
* ``vanilla``             k attempts, each judged and extracted on its own (the
  paper's "MaTTS w/o aggregation" baseline).
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ...agents.base import Agent
from ...envs.base import TextEnv, make_env
from ...provenance import WAS_DERIVED_FROM, WAS_GENERATED_BY, ProvenanceStore
from ...types import Task, Trajectory, jsonable
from .bank import ReasoningBank, Retrieved
from .induction import MemoryExtractor, refine_notes, select_best
from .schema import Experience, MemoryItem, Verdict

MEMORY_MODES = ("none", "reasoningbank")
SCALING_MODES = ("none", "parallel", "sequential", "vanilla")


@dataclass
class PipelineConfig:
    memory: str = "reasoningbank"
    scaling: str = "none"
    k: int = 1
    include_failures: bool = True
    retrieve_k: int = 1
    retrieval_mode: str = "experience"
    max_items: int | None = None
    condition_weight: float = 0.0
    utility_weight: float = 0.0
    store_steps: bool = True
    seed: int = 0

    def __post_init__(self) -> None:
        if self.memory not in MEMORY_MODES:
            raise ValueError(f"memory must be one of {MEMORY_MODES}")
        if self.scaling not in SCALING_MODES:
            raise ValueError(f"scaling must be one of {SCALING_MODES}")
        if self.k < 1:
            raise ValueError("k must be at least 1")
        if self.scaling == "none" and self.k != 1:
            raise ValueError("k > 1 needs a scaling mode")
        if self.retrieval_mode == "item" and self.max_items is None:
            self.max_items = 6


@dataclass
class TaskRecord:
    """What happened for one task of the stream."""

    task: dict[str, Any]
    trajectory_ids: list[str]
    selected: int
    score: float
    success: bool | None
    failure: str | None
    steps: int
    total_reward: float
    judged_success: bool
    judge_source: str
    attempt_scores: list[float]
    first_score: float
    best_score: float
    retrieved_item_ids: list[str] = field(default_factory=list)
    new_item_ids: list[str] = field(default_factory=list)
    experience_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return jsonable(asdict(self))


class ReasoningBankPipeline:
    """Runs a stream of tasks with (or without) reasoning memory.

    Args:
        agent: plays the episodes.
        judge: labels each trajectory success or failure (``LLMJudge`` or ``EnvJudge``).
        bank: the memory. Ignored when ``config.memory == "none"``.
        extractor: distils memory items; required when memory is enabled.
        llm: used for refinement notes and best-of-N selection under scaling.
        store: provenance store; every trajectory, verdict, item and link is recorded.
        extra_memory: given the task, returns further memory items to put in front of the
            agent besides what the bank retrieves, e.g. evidence-backed claims that
            apply under the task's conditions (``claims.report.claims_as_memory``).
        on_record: called after each task, e.g. to print progress.
    """

    def __init__(
        self,
        agent: Agent,
        judge: Any,
        *,
        bank: ReasoningBank | None = None,
        extractor: MemoryExtractor | None = None,
        llm: Any = None,
        store: ProvenanceStore | None = None,
        config: PipelineConfig | None = None,
        env_factory: Callable[[Task], TextEnv] = make_env,
        extra_memory: Callable[[Task], list[MemoryItem]] | None = None,
        on_record: Callable[[TaskRecord], None] | None = None,
    ):
        self.config = config or PipelineConfig()
        self.agent = agent
        self.judge = judge
        self.bank = bank
        self.extractor = extractor
        self.llm = llm
        self.store = store
        self.env_factory = env_factory
        self.extra_memory = extra_memory
        self.on_record = on_record
        self.records: list[TaskRecord] = []
        self._rng = random.Random(self.config.seed)
        if self.config.memory != "none" and (bank is None or extractor is None):
            raise ValueError("memory is enabled, so a bank and an extractor are required")
        if (
            self.config.scaling in ("parallel", "sequential", "vanilla")
            and self.config.k > 1
            and llm is None
        ):
            raise ValueError("test-time scaling needs an llm for selection or refinement")

    # ------------------------------------------------------------------ pieces

    def _retrieve(self, query: str, task: Task) -> list[Retrieved]:
        if self.config.memory == "none" or self.bank is None:
            return []
        c = self.config
        return self.bank.retrieve(
            query,
            k=c.retrieve_k,
            mode=c.retrieval_mode,
            max_items=c.max_items,
            conditions=task.conditions,
            condition_weight=c.condition_weight,
            utility_weight=c.utility_weight,
        )

    def _attempt(
        self,
        env: TextEnv,
        retrieved: list[Retrieved],
        *,
        sample: int,
        notes: str = "",
        group: str = "",
    ) -> Trajectory:
        first = env.reset()
        extra = self.extra_memory(env.task) if self.extra_memory is not None else []
        traj = self.agent.run(
            env,
            first_observation=first,
            memory=[r.item for r in retrieved] + extra,
            notes=notes,
            sample=sample,
            meta={
                "attempt": sample,
                "group": group,
                "retrieval": [
                    {"item": r.item.id, "experience": r.experience_id, "score": round(r.score, 4)}
                    for r in retrieved
                ],
            },
        )
        if self.store is not None:
            self.store.record_trajectory(traj, store_steps=self.config.store_steps)
            for item in extra:
                # Items rendered from claims: make the claim itself the thing that was used.
                self.store.add_node(item.id, "memory_item", label=item.title, data=item.to_dict())
                if item.meta.get("claim_id"):
                    self.store.link(item.id, WAS_DERIVED_FROM, item.meta["claim_id"])
        return traj

    def _judge(self, env: TextEnv, query: str, traj: Trajectory) -> Verdict:
        verdict = self.judge.judge(env.spec, query, traj)
        if self.store is not None:
            node = f"verdict_{traj.id}"
            self.store.add_node(node, "verdict", label=verdict.label, data=verdict.to_dict())
            self.store.link(node, WAS_DERIVED_FROM, traj.id)
            if verdict.llm_call_id:
                self.store.link(node, WAS_GENERATED_BY, verdict.llm_call_id)
        return verdict

    def _consolidate(
        self,
        task: Task,
        query: str,
        trajs: list[Trajectory],
        items: list[MemoryItem],
        call_id: str,
        verdict_label: str,
        meta: dict[str, Any],
    ) -> Experience | None:
        if self.bank is None:
            return None
        experience = self.bank.add(
            Experience(
                query=query,
                items=items,
                task_key=task.key,
                task_family=task.family,
                conditions=dict(task.conditions),
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

    # ------------------------------------------------------------------ one task

    def run_task(self, task: Task) -> TaskRecord:
        c = self.config
        env = self.env_factory(task)
        try:
            env.reset()  # some environments only know their task text after loading
            query = env.query
            retrieved = self._retrieve(query, task)
            learn = c.memory != "none"
            group = f"{task.key}#{len(self.records)}"

            trajs: list[Trajectory] = []
            verdicts: list[Verdict] = []
            notes: list[str] = []
            experiences: list[Experience] = []
            new_items: list[MemoryItem] = []

            def learn_from_single(traj: Trajectory, verdict: Verdict) -> None:
                if not learn or not (verdict.success or c.include_failures):
                    return
                assert self.extractor is not None
                items, call_id = self.extractor.extract(env.spec, query, traj, verdict)
                experience = self._consolidate(
                    task,
                    query,
                    [traj],
                    items,
                    call_id,
                    verdict.label,
                    {"judge": verdict.to_dict(), "scaling": c.scaling},
                )
                if experience is not None:
                    experiences.append(experience)
                    new_items.extend(experience.items)

            if c.scaling == "sequential" and c.k > 1:
                for attempt in range(c.k):
                    if attempt > 0:
                        note, _ = refine_notes(self.llm, env.spec, query, trajs, notes)
                        notes.append(note)
                    traj = self._attempt(
                        env, retrieved, sample=attempt, notes="\n\n".join(notes), group=group
                    )
                    trajs.append(traj)
                    verdicts.append(self._judge(env, query, traj))
                selected = len(trajs) - 1  # the refined attempt is the answer
                if learn:
                    assert self.extractor is not None
                    usable = [
                        t
                        for t, v in zip(trajs, verdicts, strict=True)
                        if v.success or c.include_failures
                    ]
                    if usable:
                        items, call_id = self.extractor.extract_refine(
                            env.spec, query, usable, notes
                        )
                        label = _combined_label(verdicts)
                        experience = self._consolidate(
                            task,
                            query,
                            usable,
                            items,
                            call_id,
                            label,
                            {"scaling": "sequential", "k": c.k, "notes": notes},
                        )
                        if experience is not None:
                            experiences.append(experience)
                            new_items.extend(experience.items)
            else:
                attempts = c.k if c.scaling in ("parallel", "vanilla") else 1
                for attempt in range(attempts):
                    traj = self._attempt(env, retrieved, sample=attempt, group=group)
                    trajs.append(traj)
                    verdicts.append(self._judge(env, query, traj))
                if attempts > 1:
                    selected, why, _ = select_best(self.llm, env.spec, query, trajs)
                else:
                    selected, why = 0, ""
                if c.scaling == "parallel" and attempts > 1:
                    if learn:
                        assert self.extractor is not None
                        usable = [
                            t
                            for t, v in zip(trajs, verdicts, strict=True)
                            if v.success or c.include_failures
                        ]
                        if usable:
                            items, call_id = self.extractor.extract_contrast(
                                env.spec, query, usable
                            )
                            experience = self._consolidate(
                                task,
                                query,
                                usable,
                                items,
                                call_id,
                                _combined_label(verdicts),
                                {"scaling": "parallel", "k": c.k, "selection": why},
                            )
                            if experience is not None:
                                experiences.append(experience)
                                new_items.extend(experience.items)
                else:
                    for traj, verdict in zip(trajs, verdicts, strict=True):
                        learn_from_single(traj, verdict)

            chosen, verdict = trajs[selected], verdicts[selected]
            if self.bank is not None and retrieved:
                # Usage statistics rely only on what the agent itself can observe:
                # the reward it received and the judged outcome.
                self.bank.record_outcome(
                    [r.item.id for r in retrieved], chosen.total_reward, verdict.success
                )
            scores = [t.outcome.score if t.outcome else 0.0 for t in trajs]
            outcome = chosen.outcome
            record = TaskRecord(
                task=task.to_dict(),
                trajectory_ids=[t.id for t in trajs],
                selected=selected,
                score=outcome.score if outcome else 0.0,
                success=outcome.success if outcome else None,
                failure=outcome.failure if outcome else None,
                steps=len(chosen.steps),
                total_reward=chosen.total_reward,
                judged_success=verdict.success,
                judge_source=verdict.source,
                attempt_scores=scores,
                first_score=scores[0],
                best_score=max(scores),
                retrieved_item_ids=[r.item.id for r in retrieved],
                new_item_ids=[i.id for i in new_items],
                experience_ids=[e.id for e in experiences],
            )
        finally:
            env.close()
        self.records.append(record)
        if self.on_record is not None:
            self.on_record(record)
        return record

    def run_stream(self, tasks: Iterable[Task]) -> list[TaskRecord]:
        """Process tasks in order; memory built from earlier tasks is available to later ones."""
        return [self.run_task(task) for task in tasks]

    # ------------------------------------------------------------------ reporting

    def summary(self) -> dict[str, Any]:
        return summarise(self.records)

    def save_records(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as fh:
            for record in self.records:
                fh.write(json.dumps(record.to_dict()) + "\n")


def _combined_label(verdicts: list[Verdict]) -> str:
    labels = {v.label for v in verdicts}
    return labels.pop() if len(labels) == 1 else "mixed"


def summarise(records: list[TaskRecord]) -> dict[str, Any]:
    """Headline metrics over a stream: mean score, success rate, steps and judge agreement."""
    n = len(records)
    if n == 0:
        return {"tasks": 0}
    known = [r for r in records if r.success is not None]
    successes = [r for r in known if r.success]
    failures = [r for r in known if not r.success]

    def mean(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 4) if values else None

    return {
        "tasks": n,
        "mean_score": mean([r.score for r in records]),
        "success_rate": mean([float(r.success) for r in known]),
        "mean_steps": mean([float(r.steps) for r in records]),
        "mean_steps_successful": mean([float(r.steps) for r in successes]),
        "mean_steps_failed": mean([float(r.steps) for r in failures]),
        "failures_by_mode": _count([r.failure for r in records if r.failure]),
        # How often the judge's label matched the simulator's own criterion.
        "judge_agreement": mean([float(r.judged_success == r.success) for r in known]),
        "mean_first_attempt_score": mean([r.first_score for r in records]),
        "mean_best_attempt_score": mean([r.best_score for r in records]),
        "new_items": sum(len(r.new_item_ids) for r in records),
    }


def _count(values: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return out
