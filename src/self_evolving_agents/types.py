"""Core records shared by environments, agents, memory and provenance.

These are plain dataclasses with explicit ``to_dict``/``from_dict`` so that a
trajectory written today can still be read after the code has moved on.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


def new_id(prefix: str) -> str:
    """Short unique identifier, e.g. ``traj_3f9a1c2b4d5e``."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def stable_hash(obj: Any, length: int = 12) -> str:
    """Deterministic hash of a JSON-serialisable object (key order independent)."""
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:length]


def jsonable(value: Any) -> Any:
    """Coerce numpy scalars/arrays and other oddities into JSON-safe values."""
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    if isinstance(value, (str, bool, int)) or value is None:
        return value
    if isinstance(value, float):
        return value if value == value and value not in (float("inf"), float("-inf")) else None
    if hasattr(value, "tolist"):  # numpy scalar or array
        return jsonable(value.tolist())
    if hasattr(value, "item"):
        return jsonable(value.item())
    return str(value)


@dataclass(frozen=True)
class Task:
    """One episode's worth of work: which environment, under which conditions, with which seed.

    ``conditions`` is the structured description of the operating regime (battery
    capacity, disturbance level, scenario difficulty, ...). It is what claims
    condition on and what condition-aware retrieval compares. ``params`` holds
    construction details that are not part of the regime (episode length, step
    limits).
    """

    env_id: str
    name: str
    seed: int = 0
    conditions: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.env_id}/{self.name}/seed={self.seed}"

    @property
    def family(self) -> str:
        """Task identity without the seed; episodes in a family differ only by randomness."""
        return f"{self.env_id}/{self.name}/{stable_hash(self.conditions, 8)}"

    def to_dict(self) -> dict[str, Any]:
        return jsonable(asdict(self))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Task:
        return cls(
            env_id=d["env_id"],
            name=d["name"],
            seed=int(d.get("seed", 0)),
            conditions=dict(d.get("conditions") or {}),
            params=dict(d.get("params") or {}),
        )


@dataclass
class Observation:
    """What the agent sees: text for language models, named numbers for rule policies.

    ``brief`` is a one-line version used when many past steps have to fit in a prompt.
    """

    text: str
    features: dict[str, float] = field(default_factory=dict)
    raw: Any = None
    brief: str = ""

    def __post_init__(self) -> None:
        if not self.brief:
            self.brief = " | ".join(line.strip() for line in self.text.splitlines()[:2])


@dataclass(frozen=True)
class Action:
    """A parsed action. ``name`` is canonical; ``args`` carries parameters if any."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        if not self.args:
            return self.name
        return json.dumps({"action": self.name, **self.args}, sort_keys=True)


@dataclass
class Step:
    """One decision: the observation it was based on, the reasoning, the action and its result.

    ``brief`` is the one-line form of the observation and ``result`` a one-line account
    of what the action did; both are what the agent itself was shown, so they are safe
    to put in front of a judge or a memory extractor.
    """

    index: int
    observation: str
    thought: str
    action: str
    reward: float
    brief: str = ""
    result: str = ""
    features: dict[str, float] = field(default_factory=dict)
    info: dict[str, Any] = field(default_factory=dict)
    llm_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return jsonable(asdict(self))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Step:
        return cls(
            index=int(d["index"]),
            observation=d.get("observation", ""),
            thought=d.get("thought", ""),
            action=d.get("action", ""),
            reward=float(d.get("reward", 0.0)),
            brief=d.get("brief", ""),
            result=d.get("result", ""),
            features=dict(d.get("features") or {}),
            info=dict(d.get("info") or {}),
            llm_call_id=d.get("llm_call_id"),
        )


@dataclass
class Outcome:
    """Ground truth about an episode, as measured by the simulator.

    This is deliberately separate from any judgement an LLM makes about the same
    episode: simulator metrics validate *what happened*, not *why*.
    """

    score: float
    success: bool | None = None
    failure: str | None = None
    terminated: bool = False
    truncated: bool = False
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return jsonable(asdict(self))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Outcome:
        return cls(
            score=float(d.get("score", 0.0)),
            success=d.get("success"),
            failure=d.get("failure"),
            terminated=bool(d.get("terminated", False)),
            truncated=bool(d.get("truncated", False)),
            metrics=dict(d.get("metrics") or {}),
        )


@dataclass
class Trajectory:
    """A complete episode with everything needed to audit or learn from it."""

    id: str
    task: Task
    query: str
    steps: list[Step] = field(default_factory=list)
    outcome: Outcome | None = None
    final_observation: str = ""
    agent: dict[str, Any] = field(default_factory=dict)
    memory_item_ids: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    @property
    def total_reward(self) -> float:
        return float(sum(s.reward for s in self.steps))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task": self.task.to_dict(),
            "query": self.query,
            "steps": [s.to_dict() for s in self.steps],
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "final_observation": self.final_observation,
            "agent": jsonable(self.agent),
            "memory_item_ids": list(self.memory_item_ids),
            "meta": jsonable(self.meta),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Trajectory:
        return cls(
            id=d["id"],
            task=Task.from_dict(d["task"]),
            query=d.get("query", ""),
            steps=[Step.from_dict(s) for s in d.get("steps", [])],
            outcome=Outcome.from_dict(d["outcome"]) if d.get("outcome") else None,
            final_observation=d.get("final_observation", ""),
            agent=dict(d.get("agent") or {}),
            memory_item_ids=list(d.get("memory_item_ids") or []),
            meta=dict(d.get("meta") or {}),
            started_at=float(d.get("started_at", 0.0)),
            finished_at=d.get("finished_at"),
        )
