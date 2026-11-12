"""Active experimentation: decide what to test next, test it, revise the graph, repeat.

Each round the planner looks at the graph and proposes experiments, most valuable
first:

1. ``test``      a hypothesis nobody has tested yet;
2. ``boundary``  two tested points on the same line disagree, so probe between them
                 (bisection) until the boundary is located to a chosen resolution;
3. ``moderator`` a supported claim carries an explanation that predicts how the
                 effect varies with some condition, so sweep that condition;
4. ``coverage``  a point of the study grid far from anything tested for this family.

Every outcome test also yields the mediator checks of the claim's explanations for
free, because both arms' full metrics are already there.

Each family is tested against the reference policy, one change at a time. Whether
the recommended settings still work when *combined* is checked separately (see
``evaluate.composition_check``).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .graph import ClaimGraph
from .schema import A_BETTER, DECISIVE, RETIRED, SUPPORTED, Claim, Evidence, log_distance
from .testing import ABResult, ClaimTester, Domain


@dataclass
class Proposal:
    """One experiment the planner would like to run."""

    kind: str
    root_id: str
    conditions: dict[str, float]
    priority: float
    reason: str
    mechanism: int | None = None
    levels: list[float] = field(default_factory=list)

    def key(self, domain: Domain) -> tuple[Any, ...]:
        point = tuple(sorted(domain.explored(self.conditions).items()))
        return (
            self.kind if self.kind == "moderator" else "outcome",
            self.root_id,
            point,
            self.mechanism,
        )


def _round_sig(value: float, digits: int = 3) -> float:
    if value == 0:
        return 0.0
    return round(value, digits - 1 - int(math.floor(math.log10(abs(value)))))


class Planner:
    """Proposes experiments from the current state of the graph.

    Args:
        boundary_ratio: stop bisecting once two disagreeing neighbours are within this
            factor of each other (1.25 locates a boundary to within 25%).
        coverage: whether to propose untested grid points once nothing more urgent
            is left.
        sweeps: levels to use for moderator sweeps over conditions that are not
            explored variables of the domain.
    """

    def __init__(
        self,
        graph: ClaimGraph,
        domain: Domain,
        *,
        boundary_ratio: float = 1.25,
        coverage: bool = True,
        sweeps: dict[str, list[float]] | None = None,
    ):
        self.graph = graph
        self.domain = domain
        self.boundary_ratio = boundary_ratio
        self.coverage = coverage
        self.sweeps = {k: sorted(v) for k, v in (sweeps or {}).items()}
        self.skip: set[tuple[Any, ...]] = set()

    def _anchor(self, root: Claim) -> dict[str, float] | None:
        """Where to test a fresh hypothesis: its stated context, else the reference point."""
        context = root.origin.get("context") or {}
        candidate = self.domain.conditions(
            **{k: v for k, v in context.items() if k in self.domain.variables}
        )
        if root.scope.contains(candidate):
            return candidate
        anchor = self.domain.explored(self.domain.anchor())
        inside = [g for g in self.domain.grid() if root.scope.contains(g)]
        if not inside:
            return None
        variables = list(self.domain.variables)
        return min(inside, key=lambda g: log_distance(self.domain.explored(g), anchor, variables))

    def _boundaries(self, root: Claim, pool: list[Evidence]) -> list[Proposal]:
        """Probe between neighbouring tested points whose results differ.

        All tested points count, including unresolved ones, so an inconclusive midpoint
        between a "better" and a "worse" result is itself bracketed further, until
        neighbours are within ``boundary_ratio`` of each other.
        """
        out: list[Proposal] = []
        if not any(e.label in DECISIVE for e in pool):
            return out
        for var in self.domain.variables:
            lines: dict[tuple[Any, ...], list[Evidence]] = {}
            for e in pool:
                others = tuple(sorted((k, v) for k, v in e.conditions.items() if k != var))
                lines.setdefault(others, []).append(e)
            for others, members in lines.items():
                members.sort(key=lambda e: e.conditions[var])
                values = [e.conditions[var] for e in members]
                for a, b in zip(members, members[1:], strict=False):
                    low, high = a.conditions[var], b.conditions[var]
                    if a.label == b.label or low <= 0 or high / low <= self.boundary_ratio:
                        continue
                    mid = _round_sig(math.sqrt(low * high))
                    if not low < mid < high or any(abs(math.log(v / mid)) < 0.03 for v in values):
                        continue
                    out.append(
                        Proposal(
                            "boundary",
                            root.id,
                            self.domain.conditions(**{**dict(others), var: mid}),
                            80.0 + min(math.log(high / low), 2.0),
                            f"{var}={low:g} gave '{a.label}' but {var}={high:g} gave '{b.label}'; "
                            f"probing {mid:g} to locate the boundary",
                        )
                    )
        return out

    def _moderators(self, root: Claim, pool: list[Evidence]) -> list[Proposal]:
        supporting = [e for e in pool if e.label == A_BETTER]
        if not supporting:
            return []
        best = max(supporting, key=lambda e: e.ci_low)
        out = []
        for index, mechanism in enumerate(root.mechanisms):
            if not mechanism.moderator or not mechanism.moderator_direction:
                continue
            if any(e.kind == "moderator" for e in mechanism.evidence):
                continue
            levels = self.sweeps.get(mechanism.moderator) or self.domain.variables.get(
                mechanism.moderator, []
            )
            if len(levels) < 2:
                continue
            out.append(
                Proposal(
                    "moderator",
                    root.id,
                    self.domain.conditions(**best.conditions),
                    60.0,
                    f"explanation '{mechanism.statement}' predicts the effect changes with "
                    f"{mechanism.moderator}; sweeping {levels}",
                    mechanism=index,
                    levels=list(levels),
                )
            )
        return out

    def _coverage(self, root: Claim, pool: list[Evidence]) -> list[Proposal]:
        variables = list(self.domain.variables)
        tested = [e.conditions for e in pool]
        out = []
        for point in self.domain.grid():
            explored = self.domain.explored(point)
            if explored in tested or not root.scope.contains(point):
                continue
            distance = min(log_distance(explored, t, variables) for t in tested)
            out.append(
                Proposal(
                    "coverage",
                    root.id,
                    point,
                    30.0 + 10.0 * min(distance, 2.0),
                    "untested point of the study grid, "
                    f"{distance:.2f} log-units from the nearest test of this comparison",
                )
            )
        return sorted(out, key=lambda p: -p.priority)[:2]

    def propose(self) -> list[Proposal]:
        proposals: list[Proposal] = []
        for root in self.graph.roots():
            if root.status == RETIRED:
                continue
            pool = [e for e in root.evidence if e.kind == "outcome"]
            if not pool:
                anchor = self._anchor(root)
                if anchor is not None:
                    proposals.append(
                        Proposal(
                            "test", root.id, anchor, 100.0, "hypothesis has not been tested yet"
                        )
                    )
                continue
            proposals += self._boundaries(root, pool)
            proposals += self._moderators(root, pool)
            if self.coverage:
                proposals += self._coverage(root, pool)
        proposals = [p for p in proposals if p.key(self.domain) not in self.skip]
        return sorted(proposals, key=lambda p: -p.priority)


class ActiveLoop:
    """Runs the propose -> test -> revise cycle within an episode budget.

    Args:
        budget_episodes: stop once this many simulator episodes have actually been run
            (cached episodes are free). The round in progress is allowed to finish.
        per_round: how many proposals to execute before looking at the graph again.
        proposers: objects with ``propose(graph) -> list[Claim]``, asked for new
            hypotheses at the start of every round.
        on_event: called with each revision-log entry as it is produced.
    """

    def __init__(
        self,
        graph: ClaimGraph,
        tester: ClaimTester,
        planner: Planner,
        *,
        budget_episodes: int,
        per_round: int = 3,
        proposers: list[Any] | None = None,
        moderator_seeds: int | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.graph = graph
        self.tester = tester
        self.planner = planner
        self.budget = budget_episodes
        self.per_round = per_round
        self.proposers = proposers or []
        self.moderator_seeds = moderator_seeds or min(2 * tester.batch, tester.max_seeds)
        self.on_event = on_event
        self.rounds = 0
        self.experiments: list[dict[str, Any]] = []

    def _emit(self, entries: list[dict[str, Any]]) -> None:
        if self.on_event is not None:
            for entry in entries:
                self.on_event(entry)

    def _check_mediators(self, root: Claim, ab: ABResult, evidence: Evidence) -> None:
        """Wherever the effect appeared, check whether each explanation's mediator moved."""
        if evidence.label != A_BETTER:
            return
        for index, mechanism in enumerate(root.mechanisms):
            mediator = self.tester.mediator_evidence(mechanism, ab)
            if mediator is not None:
                self._emit([self.graph.record_mechanism(root.id, index, mediator)])

    def _run_outcome(self, proposal: Proposal) -> None:
        root = self.graph.get(proposal.root_id)
        ab, evidence = self.tester.test_claim_at(root, proposal.conditions)
        evidence.details["purpose"] = proposal.kind
        evidence.details["reason"] = proposal.reason
        self._emit(self.graph.record(root.id, evidence))
        self._check_mediators(root, ab, evidence)

    def _run_moderator(self, proposal: Proposal) -> None:
        root = self.graph.get(proposal.root_id)
        assert proposal.mechanism is not None
        mechanism = root.mechanisms[proposal.mechanism]
        assert mechanism.moderator is not None
        by_level: dict[float, ABResult] = {}
        for level in proposal.levels:
            conditions = {**proposal.conditions, mechanism.moderator: float(level)}
            by_level[level] = self.tester.run_ab(
                conditions, root.intervention, root.baseline, self.moderator_seeds
            )
        evidence = self.tester.moderator_evidence(root, mechanism, by_level)
        if evidence is not None:
            evidence.details["reason"] = proposal.reason
            self._emit([self.graph.record_mechanism(root.id, proposal.mechanism, evidence)])
        if mechanism.moderator in self.tester.domain.variables:
            # The sweep also told us how the comparison fares at each level; keep that.
            for ab in by_level.values():
                outcome = self.tester.outcome_evidence(root, ab)
                outcome.details["purpose"] = "moderator-sweep"
                outcome.details["background"] = {}
                self._emit(self.graph.record(root.id, outcome))

    def step(self) -> int:
        """One round. Returns the number of experiments executed."""
        for proposer in self.proposers:
            for claim in proposer.propose(self.graph):
                if self.graph.find_duplicate(claim) is None:
                    self.graph.add(claim, reason=claim.origin.get("note", "proposed"))
                    self._emit(self.graph.log[-1:])
        executed = 0
        seen: set[tuple[Any, ...]] = set()
        for proposal in self.planner.propose():
            key = proposal.key(self.tester.domain)
            if key in seen:
                continue
            seen.add(key)
            before = self.tester.episodes
            if proposal.kind == "moderator":
                self._run_moderator(proposal)
            else:
                self._run_outcome(proposal)
            # A proposal is never repeated: an inconclusive test already used every seed allowed.
            self.planner.skip.add(key)
            self.experiments.append(
                {
                    "round": self.rounds,
                    "kind": proposal.kind,
                    "family": proposal.root_id,
                    "conditions": self.tester.domain.explored(proposal.conditions),
                    "reason": proposal.reason,
                    "episodes": self.tester.episodes - before,
                }
            )
            executed += 1
            if executed >= self.per_round or self.tester.episodes >= self.budget:
                break
        self.rounds += 1
        return executed

    def run(self, max_rounds: int = 1000) -> dict[str, Any]:
        """Iterate until the budget is spent or the planner has nothing left to propose."""
        while self.tester.episodes < self.budget and self.rounds < max_rounds:
            if self.step() == 0:
                break
        return {
            "rounds": self.rounds,
            "experiments": len(self.experiments),
            "episodes_run": self.tester.episodes,
            "budget": self.budget,
            "graph": self.graph.summary(),
        }


class LadderProposer:
    """Proposes new settings to try, by two simple rules over a ladder of candidate values.

    * *Keep going*: when a supported claim says value ``w`` beats value ``l``, and the
      ladder has a next value beyond ``w`` on the side away from ``l``, hypothesise
      that the next value beats ``w``.
    * *Nothing works here*: when a test shows both settings failing often at some
      point, neither is acceptable there, and the outcome says nothing about which
      direction would help. Hypothesise one step outward on each side.

    This is plain coordinate search, but every step is a claim with a scope, evidence
    and a place in the graph. New claims are unscoped; their ``context`` says where
    the motivating result was, which is where they are tested first.
    """

    def __init__(
        self,
        ladders: dict[str, list[float]],
        env_id: str = "bsk-scan",
        failure_rate: float = 0.25,
    ):
        self.ladders = {p: sorted(v) for p, v in ladders.items()}
        self.env_id = env_id
        self.failure_rate = failure_rate

    def _candidate(
        self,
        root: Claim,
        parameter: str,
        value: float,
        against: float,
        context: dict[str, float],
        rule: str,
        source: str,
    ) -> Claim:
        reason = (
            "Going further in the direction that helped keeps helping"
            if rule == "keep-going"
            else "Neither tested setting is acceptable here; a setting further out does better"
        )
        return Claim(
            statement=f"{reason}: {parameter}={value:g} beats {parameter}={against:g}.",
            intervention={parameter: value},
            baseline={parameter: against},
            metric=root.metric,
            min_effect=root.min_effect,
            env_id=root.env_id,
            origin={
                "author": "program",
                "rule": rule,
                "from": source,
                "context": dict(context),
                "note": f"{rule} rule, from {source}, along the {parameter} ladder",
            },
        )

    @staticmethod
    def _failure_rate(arm: dict[str, Any], n: int) -> float:
        return sum(arm.get("failures", {}).values()) / max(n, 1)

    def propose(self, graph: ClaimGraph) -> list[Claim]:
        out: list[Claim] = []

        def offer(candidate: Claim) -> None:
            duplicate = graph.find_duplicate(candidate) is not None or any(
                {tuple(c.intervention.items()), tuple(c.baseline.items())}
                == {tuple(candidate.intervention.items()), tuple(candidate.baseline.items())}
                for c in out
            )
            if not duplicate:
                out.append(candidate)

        for root in graph.roots():
            if len(root.parameters) != 1 or root.parameters[0] not in self.ladders:
                continue
            parameter = root.parameters[0]
            ladder = self.ladders[parameter]

            for claim in graph.active(root.id):
                if claim.status != SUPPORTED:
                    continue
                winner, loser = claim.intervention[parameter], claim.baseline[parameter]
                if winner not in ladder:
                    continue
                index = ladder.index(winner) + (1 if winner > loser else -1)
                if not 0 <= index < len(ladder):
                    continue
                supporting = [e for e in claim.outcome_evidence() if e.verdict == "supports"]
                context = max(supporting, key=lambda e: e.ci_low).conditions if supporting else {}
                offer(
                    self._candidate(
                        root, parameter, ladder[index], winner, context, "keep-going", claim.id
                    )
                )

            pair = sorted((root.intervention[parameter], root.baseline[parameter]))
            if pair[0] not in ladder or pair[1] not in ladder:
                continue
            for evidence in root.evidence:
                if evidence.kind != "outcome":
                    continue
                arms = (evidence.details.get("treatment", {}), evidence.details.get("control", {}))
                if min(self._failure_rate(arm, evidence.n) for arm in arms) < self.failure_rate:
                    continue
                above, below = ladder.index(pair[1]) + 1, ladder.index(pair[0]) - 1
                if above < len(ladder):
                    offer(
                        self._candidate(
                            root,
                            parameter,
                            ladder[above],
                            pair[1],
                            evidence.conditions,
                            "nothing-works-here",
                            root.id,
                        )
                    )
                if below >= 0:
                    offer(
                        self._candidate(
                            root,
                            parameter,
                            ladder[below],
                            pair[0],
                            evidence.conditions,
                            "nothing-works-here",
                            root.id,
                        )
                    )
        return out
