"""The investigation memory as a graph: three kinds of node, and the links between them.

=====================  =============================================  ================
Node                   What it holds                                  Scope
=====================  =============================================  ================
evidence               a measurement or observation from one episode  the world it came from
hypothesis             a statement about how a world works, with the  where it was observed,
                       conditions it was observed under, its status,  stated as conditions
                       and the evidence for and against it
strategy               a way of investigating, with when it applies,  meant to transfer
                       a test that puts it into practice, the
                       episodes it came from and its record of use
=====================  =============================================  ================

Links: ``supported_by`` and ``contradicted_by`` (hypothesis to evidence),
``derived_from`` (hypothesis and strategy to the episode), ``revised_into``
(strategy to the strategy that replaced it), ``used_in`` (strategy to the episodes
where it was retrieved, with the assessment of that use).

A *world* is one DiscoveryWorld scenario at one difficulty and one seed. The memory
records which world each item came from; this is bookkeeping, like provenance, and
uses nothing an agent could not know (the seed is not shown to the agent, but the
memory knows which episode it is learning from). Whether a finding holds in another
world is exactly what it does not know.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ...types import new_id


def world_of(task: Any) -> dict[str, Any]:
    """The world a task is set in: scenario, difficulty, seed (or the task's own terms)."""
    conditions = dict(getattr(task, "conditions", {}) or {})
    return {
        "scenario": conditions.get("scenario", getattr(task, "name", "")),
        "difficulty": conditions.get("difficulty", ""),
        "seed": int(getattr(task, "seed", 0)),
    }


def world_key(world: dict[str, Any]) -> str:
    return f"{world['scenario']}/{world['difficulty']}/seed={world['seed']}"


def theme_key(world: dict[str, Any]) -> str:
    """Worlds of one kind: same scenario and difficulty, any seed."""
    return f"{world['scenario']}/{world['difficulty']}"


@dataclass
class Evidence:
    text: str
    world: dict[str, Any]
    episode: str
    step: int | None = None
    id: str = field(default_factory=lambda: new_id("ev"))


@dataclass
class Hypothesis:
    statement: str
    conditions: str
    status: str  # "supported" | "refuted" | "open"
    world: dict[str, Any]
    episode: str
    supported_by: list[str] = field(default_factory=list)
    contradicted_by: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("hyp"))


@dataclass
class Strategy:
    statement: str
    applies_when: str
    test: str
    basis: str
    derived_from: list[str]
    worlds: list[str]
    uses: int = 0
    helped: int = 0
    did_not_help: int = 0
    record: list[dict[str, Any]] = field(default_factory=list)
    status: str = "active"  # "active" | "replaced"
    revised_from: str | None = None
    id: str = field(default_factory=lambda: new_id("str"))

    @property
    def utility(self) -> float:
        """Share of assessed uses in which it helped, with one imaginary use of each kind."""
        return (self.helped + 1) / (self.helped + self.did_not_help + 2)


STATUSES = ("supported", "refuted", "open")


class InvestigationGraph:
    """All three kinds of node, kept in one JSON file that is rewritten after each change."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.evidence: dict[str, Evidence] = {}
        self.hypotheses: dict[str, Hypothesis] = {}
        self.strategies: dict[str, Strategy] = {}
        self.episodes: list[dict[str, Any]] = []
        if self.path is not None and self.path.exists():
            self._load()

    # ------------------------------------------------------------------ storage

    def _load(self) -> None:
        assert self.path is not None
        data = json.loads(self.path.read_text())
        self.evidence = {d["id"]: Evidence(**d) for d in data.get("evidence", [])}
        self.hypotheses = {d["id"]: Hypothesis(**d) for d in data.get("hypotheses", [])}
        self.strategies = {d["id"]: Strategy(**d) for d in data.get("strategies", [])}
        self.episodes = list(data.get("episodes", []))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "evidence": [asdict(e) for e in self.evidence.values()],
            "hypotheses": [asdict(h) for h in self.hypotheses.values()],
            "strategies": [asdict(s) for s in self.strategies.values()],
            "episodes": self.episodes,
            "links": self.links(),
        }

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=1))
        os.replace(tmp, self.path)

    # ------------------------------------------------------------------ queries

    def links(self) -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []
        for h in self.hypotheses.values():
            out += [(h.id, "supported_by", e) for e in h.supported_by]
            out += [(h.id, "contradicted_by", e) for e in h.contradicted_by]
            out.append((h.id, "derived_from", h.episode))
        for s in self.strategies.values():
            out += [(s.id, "derived_from", e) for e in s.derived_from]
            out += [(s.id, "used_in", r["episode"]) for r in s.record]
            if s.revised_from:
                out.append((s.revised_from, "revised_into", s.id))
        return out

    def active_strategies(self) -> list[Strategy]:
        return [s for s in self.strategies.values() if s.status == "active"]

    def hypotheses_in(self, world: dict[str, Any]) -> list[Hypothesis]:
        key = world_key(world)
        return [h for h in self.hypotheses.values() if world_key(h.world) == key]

    def hypotheses_elsewhere(self, world: dict[str, Any]) -> list[Hypothesis]:
        """Hypotheses from other worlds of the same kind (same scenario and difficulty)."""
        key, theme = world_key(world), theme_key(world)
        return [
            h
            for h in self.hypotheses.values()
            if theme_key(h.world) == theme and world_key(h.world) != key
        ]

    def evidence_in(self, world: dict[str, Any]) -> list[Evidence]:
        key = world_key(world)
        return [e for e in self.evidence.values() if world_key(e.world) == key]

    def counts(self) -> dict[str, Any]:
        return {
            "evidence": len(self.evidence),
            "hypotheses": len(self.hypotheses),
            "hypotheses_by_status": {
                status: sum(1 for h in self.hypotheses.values() if h.status == status)
                for status in STATUSES
            },
            "strategies": len(self.active_strategies()),
            "strategies_replaced": sum(
                1 for s in self.strategies.values() if s.status == "replaced"
            ),
            "episodes": len(self.episodes),
        }
