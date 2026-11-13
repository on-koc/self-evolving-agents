"""Test-time learning over a stream of tasks: the loop every model-driven method shares.

Tasks arrive one at a time and are completed in order, without access to later ones
(the setting of the ReasoningBank paper, section 3.1). A method is the combination of
three parts, and this module owns none of their behaviour:

* an **agent** plays an episode (``agents/``);
* a **memory** decides what is put in front of the agent before the episode and what
  is learned from it afterwards (:class:`Memory`; the base class is "no memory");
* a **scaling** strategy decides how many attempts a task gets and how they are
  combined (:class:`Scaling`; the base class is one attempt).

Each method folder supplies its own memory and/or scaling class. Nothing in here
imports from a method folder, so that no method can leak into another through the
loop.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..agents.base import Agent, MemoryBlock
from ..envs.base import EnvSpec, TextEnv, make_env
from ..provenance import WAS_DERIVED_FROM, WAS_GENERATED_BY, ProvenanceStore
from ..types import Task, Trajectory, jsonable

# --------------------------------------------------------------------------- judging


@dataclass
class Verdict:
    """A judgement of whether an episode succeeded, and who made it.

    ``source`` is ``"llm"`` for an LLM-as-a-judge working without ground truth, or
    ``"env"`` when the simulator's own success criterion was used.
    """

    success: bool
    thoughts: str = ""
    source: str = "llm"
    llm_call_id: str | None = None

    @property
    def label(self) -> str:
        return "success" if self.success else "failure"

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "thoughts": self.thoughts,
            "source": self.source,
            "llm_call_id": self.llm_call_id,
        }


class Judge(Protocol):
    source: str

    def judge(self, spec: EnvSpec, query: str, traj: Trajectory) -> Verdict: ...


class EnvJudge:
    """Labels an episode with the simulator's own success criterion.

    This is ground truth, which the test-time-learning setting does not provide. It is
    here as a control: it corresponds to the 100%-accurate judge of the paper's
    robustness analysis and to ``--criteria gt`` in the reference code, and it removes
    judge error from a comparison when that is what one wants to isolate.
    """

    source = "env"

    def judge(self, spec: EnvSpec, query: str, traj: Trajectory) -> Verdict:
        outcome = traj.outcome
        if outcome is None or outcome.success is None:
            raise ValueError("the environment reported no success criterion for this episode")
        reason = (
            "ground-truth criterion met" if outcome.success else "ground-truth criterion not met"
        )
        if outcome.failure:
            reason += f" (failure mode: {outcome.failure})"
        return Verdict(success=bool(outcome.success), thoughts=reason, source="env")


# --------------------------------------------------------------------------- memory


@dataclass
class Retrieval:
    """What a memory retrieved for one task: the block for the agent, and how it was chosen."""

    block: MemoryBlock = field(default_factory=MemoryBlock)
    details: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Learned:
    """Records a memory created from one task."""

    item_ids: list[str] = field(default_factory=list)
    experience_ids: list[str] = field(default_factory=list)

    def extend(self, other: Learned) -> Learned:
        self.item_ids += other.item_ids
        self.experience_ids += other.experience_ids
        return self


class Memory:
    """Interface of a memory method. This base class is the no-memory method."""

    name = "none"
    #: Whether anything is learned after a task. A memory that learns needs a judge.
    learns = False

    def retrieve(self, env: TextEnv, task: Task, query: str) -> Retrieval:
        return Retrieval()

    def learn_single(
        self, env: TextEnv, task: Task, query: str, traj: Trajectory, verdict: Verdict
    ) -> Learned:
        """Learn from one finished, judged trajectory."""
        return Learned()

    def record_use(self, retrieval: Retrieval, traj: Trajectory, verdict: Verdict | None) -> None:
        """Called once per task with the attempt that counted. For bookkeeping only."""

    def stats(self) -> dict[str, Any]:
        return {}


# --------------------------------------------------------------------------- scaling


@dataclass
class Attempts:
    """The attempts made at one task and which of them counts as its result."""

    trajectories: list[Trajectory]
    verdicts: list[Verdict | None]
    selected: int = 0
    notes: list[str] = field(default_factory=list)
    selection: str = ""


class Scaling:
    """How many attempts a task gets. This base class is one attempt: no scaling."""

    name = "none"
    k = 1

    def attempts(
        self, loop: StreamLoop, env: TextEnv, task: Task, query: str, retrieval: Retrieval
    ) -> Attempts:
        traj = loop.attempt(env, retrieval, sample=0, group=loop.group(task))
        return Attempts([traj], [loop.judge_trajectory(env, query, traj)])

    def learn(
        self, loop: StreamLoop, env: TextEnv, task: Task, query: str, attempts: Attempts
    ) -> Learned:
        return loop.learn_single(env, task, query, attempts.trajectories[0], attempts.verdicts[0])


# --------------------------------------------------------------------------- records


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
    judged_success: bool | None
    judge_source: str
    attempt_scores: list[float]
    attempt_successes: list[bool | None]
    first_score: float
    best_score: float
    retrieved_item_ids: list[str] = field(default_factory=list)
    new_item_ids: list[str] = field(default_factory=list)
    experience_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return jsonable(asdict(self))


class StreamLoop:
    """Runs a stream of tasks through an agent, a memory and a scaling strategy.

    Args:
        agent: plays the episodes.
        memory: defaults to no memory.
        scaling: defaults to one attempt per task.
        judge: labels each trajectory. Required when the memory learns; optional
            otherwise (without one, ``judged_success`` is not recorded and no judge
            calls are made).
        store: provenance store; every trajectory and verdict is recorded, and the
            memory records what it creates.
        on_record: called after each task, e.g. to print progress.
    """

    def __init__(
        self,
        agent: Agent,
        *,
        memory: Memory | None = None,
        scaling: Scaling | None = None,
        judge: Judge | None = None,
        store: ProvenanceStore | None = None,
        env_factory: Callable[[Task], TextEnv] = make_env,
        on_record: Callable[[TaskRecord], None] | None = None,
        store_steps: bool = True,
    ):
        self.agent = agent
        self.memory = memory or Memory()
        self.scaling = scaling or Scaling()
        self.judge = judge
        self.store = store
        self.env_factory = env_factory
        self.on_record = on_record
        self.store_steps = store_steps
        self.records: list[TaskRecord] = []
        if self.memory.learns and judge is None:
            raise ValueError(
                f"the {self.memory.name} memory learns from verdicts and needs a judge"
            )

    # ------------------------------------------------------------------ pieces

    def group(self, task: Task) -> str:
        """Label shared by all attempts at the current task."""
        return f"{task.key}#{len(self.records)}"

    def attempt(
        self, env: TextEnv, retrieval: Retrieval, *, sample: int, notes: str = "", group: str = ""
    ) -> Trajectory:
        """One episode from the start, with the retrieved memory in front of the agent."""
        first = env.reset()
        traj = self.agent.run(
            env,
            first_observation=first,
            memory=retrieval.block,
            notes=notes,
            sample=sample,
            meta={"attempt": sample, "group": group, "retrieval": retrieval.details},
        )
        if self.store is not None:
            self.store.record_trajectory(traj, store_steps=self.store_steps)
        return traj

    def judge_trajectory(self, env: TextEnv, query: str, traj: Trajectory) -> Verdict | None:
        if self.judge is None:
            return None
        verdict = self.judge.judge(env.spec, query, traj)
        if self.store is not None:
            node = f"verdict_{traj.id}"
            self.store.add_node(node, "verdict", label=verdict.label, data=verdict.to_dict())
            self.store.link(node, WAS_DERIVED_FROM, traj.id)
            if verdict.llm_call_id:
                self.store.link(node, WAS_GENERATED_BY, verdict.llm_call_id)
        return verdict

    def learn_single(
        self, env: TextEnv, task: Task, query: str, traj: Trajectory, verdict: Verdict | None
    ) -> Learned:
        if not self.memory.learns or verdict is None:
            return Learned()
        return self.memory.learn_single(env, task, query, traj, verdict)

    # ------------------------------------------------------------------ one task

    def run_task(self, task: Task) -> TaskRecord:
        env = self.env_factory(task)
        try:
            env.reset()  # some environments only know their task text after loading
            query = env.query
            retrieval = self.memory.retrieve(env, task, query)
            attempts = self.scaling.attempts(self, env, task, query, retrieval)
            learned = self.scaling.learn(self, env, task, query, attempts)

            chosen = attempts.trajectories[attempts.selected]
            verdict = attempts.verdicts[attempts.selected]
            self.memory.record_use(retrieval, chosen, verdict)
            outcomes = [t.outcome for t in attempts.trajectories]
            scores = [o.score if o else 0.0 for o in outcomes]
            outcome = chosen.outcome
            record = TaskRecord(
                task=task.to_dict(),
                trajectory_ids=[t.id for t in attempts.trajectories],
                selected=attempts.selected,
                score=outcome.score if outcome else 0.0,
                success=outcome.success if outcome else None,
                failure=outcome.failure if outcome else None,
                steps=len(chosen.steps),
                total_reward=chosen.total_reward,
                judged_success=verdict.success if verdict else None,
                judge_source=verdict.source if verdict else "",
                attempt_scores=scores,
                attempt_successes=[o.success if o else None for o in outcomes],
                first_score=scores[0],
                best_score=max(scores),
                retrieved_item_ids=list(retrieval.block.item_ids),
                new_item_ids=learned.item_ids,
                experience_ids=learned.experience_ids,
            )
        finally:
            env.close()
        self.records.append(record)
        if self.on_record is not None:
            self.on_record(record)
        return record

    def run_stream(self, tasks: Iterable[Task]) -> list[TaskRecord]:
        """Process tasks in order; what was learned from earlier tasks is available to later ones."""
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


def load_records(path: str | Path) -> list[TaskRecord]:
    """Read back the records of a run."""
    with Path(path).open() as fh:
        return [TaskRecord(**json.loads(line)) for line in fh if line.strip()]


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _count(values: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return out


def summarise(records: list[TaskRecord]) -> dict[str, Any]:
    """Headline metrics over a stream. Every one is defined in ``docs/metrics.md``."""
    n = len(records)
    if n == 0:
        return {"tasks": 0}
    known = [r for r in records if r.success is not None]
    successes = [r for r in known if r.success]
    failures = [r for r in known if not r.success]
    judged = [r for r in known if r.judged_success is not None]
    firsts = [r.attempt_successes[0] for r in records if r.attempt_successes[0] is not None]
    anys = [
        any(bool(s) for s in r.attempt_successes)
        for r in records
        if all(s is not None for s in r.attempt_successes)
    ]
    return {
        "tasks": n,
        "mean_score": _mean([r.score for r in records]),
        "success_rate": _mean([float(r.success) for r in known]),
        "failure_rate": _mean([float(r.failure is not None) for r in records]),
        "failures_by_mode": _count([r.failure for r in records if r.failure]),
        "mean_steps": _mean([float(r.steps) for r in records]),
        "mean_steps_successful": _mean([float(r.steps) for r in successes]),
        "mean_steps_failed": _mean([float(r.steps) for r in failures]),
        # How often the judge's label matched the simulator's own criterion, and in
        # which direction it erred.
        "judge_agreement": _mean([float(r.judged_success == r.success) for r in judged]),
        "judge_false_success": sum(1 for r in judged if r.judged_success and not r.success),
        "judge_false_failure": sum(1 for r in judged if not r.judged_success and r.success),
        "judged_tasks": len(judged),
        # Under test-time scaling: the first attempt (one draw), the attempt selected
        # as the task's result (``mean_score`` above) and the best of all attempts.
        "mean_first_attempt_score": _mean([r.first_score for r in records]),
        "first_attempt_success_rate": _mean([float(s) for s in firsts]),
        "mean_best_attempt_score": _mean([r.best_score for r in records]),
        "any_attempt_success_rate": _mean([float(s) for s in anys]),
        "new_items": sum(len(r.new_item_ids) for r in records),
    }
