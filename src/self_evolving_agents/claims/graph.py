"""The claim graph: claims, the evidence behind them, and how they were revised.

Claims are grouped into *families*. A family is one comparison ("this setting versus
that one") studied across condition space. Its root claim holds the pooled evidence;
when that evidence disagrees with itself, the family is partitioned into regions and
each region becomes a more specific claim:

* a region where the intervention won keeps the root's claim, narrowed to the region;
* a region where the baseline won becomes the *reversed* claim for that region;
* a region where the intervention brought no meaningful benefit, or where the test
  stayed inconclusive, gets no claim (nothing established, nothing to recommend).

Nothing is deleted. A superseded root keeps every test that contradicted it, and
each specialised claim keeps the counterexamples that fixed its boundary, so "where
does this stop working, and how do we know?" always has an answer.

Relations recorded between claims: ``specializes`` (child -> root), ``contradicts``
(reversed child -> root), ``supersedes`` (children -> a root they replaced) and
``requires`` (a claim -> claims whose settings were in force when it was tested).
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .schema import (
    A_BETTER,
    B_BETTER,
    CONTESTED,
    CONTRADICTS,
    DECISIVE,
    HYPOTHESIS,
    INCONCLUSIVE,
    NO_BENEFIT,
    REFUTED,
    RETIRED,
    SUPERSEDED,
    SUPPORTED,
    SUPPORTS,
    Claim,
    Evidence,
    Region,
    log_distance,
)

if TYPE_CHECKING:
    from ..provenance import ProvenanceStore

SPECIALIZES = "specializes"
CONTRADICTS_REL = "contradicts"
SUPERSEDES = "supersedes"
REQUIRES = "requires"
MIXED = "mixed"


@dataclass
class Leaf:
    """One region of a family's partition and the label its evidence agrees on."""

    region: Region
    label: str
    points: list[tuple[dict[str, float], str]]


def _threshold(low: float, high: float) -> float:
    """Split point between two tested values: geometric mean for positive quantities."""
    return math.sqrt(low * high) if low > 0 and high > 0 else (low + high) / 2.0


def _impurity(points: list[tuple[dict[str, float], str]]) -> float:
    if not points:
        return 0.0
    counts: dict[str, int] = {}
    for _, label in points:
        counts[label] = counts.get(label, 0) + 1
    return 1.0 - sum((c / len(points)) ** 2 for c in counts.values())


def partition(
    points: list[tuple[dict[str, float], str]], region: Region, max_depth: int = 3
) -> list[Leaf]:
    """Recursively split condition space so that each region's evidence agrees.

    A small decision tree over the tested points: at each step, choose the variable
    and threshold (between two adjacent tested values) that best separates the
    labels. Splitting stops when a region is pure, cannot be split, or the depth
    limit is reached; a region that is still impure is labelled ``mixed``.

    A split is made even when it does not reduce the disagreement by itself, as long
    as it separates tested points: with two variables, results can disagree in a
    checkerboard that takes two splits to pull apart. Along a single variable some
    split always reduces the disagreement, so this makes no difference there.
    """
    labels = {label for _, label in points}
    if len(labels) <= 1 or max_depth == 0:
        label = labels.pop() if len(labels) == 1 else (MIXED if labels else "")
        return [Leaf(region, label, points)]
    best: tuple[float, str, float] | None = None
    for var in sorted({v for conditions, _ in points for v in conditions}):
        values = sorted({conditions[var] for conditions, _ in points})
        for low, high in zip(values, values[1:], strict=False):
            t = _threshold(low, high)
            left = [p for p in points if p[0][var] < t]
            right = [p for p in points if p[0][var] >= t]
            score = (_impurity(left) * len(left) + _impurity(right) * len(right)) / len(points)
            if best is None or score < best[0] - 1e-12:
                best = (score, var, t)
    if best is None:
        return [Leaf(region, MIXED, points)]
    _, var, t = best
    left = [p for p in points if p[0][var] < t]
    right = [p for p in points if p[0][var] >= t]
    return partition(left, region.restrict(var, high=t), max_depth - 1) + partition(
        right, region.restrict(var, low=t), max_depth - 1
    )


class ClaimGraph:
    """Store of claims with evidence-driven revision.

    Args:
        path: JSON file to persist to (``None`` keeps the graph in memory).
        store: provenance store to mirror claims, evidence and relations into.
        max_depth: how many times in a row a family's condition space may be split
            when its evidence disagrees. A region still holding conflicting results
            at that depth becomes a ``contested`` claim, which is never applied.
            Three is enough for one condition variable with a few changes of
            verdict along it; use more with two or more variables.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        store: ProvenanceStore | None = None,
        max_depth: int = 3,
    ):
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        self.path = Path(path) if path else None
        self.store = store
        self.max_depth = int(max_depth)
        self.claims: dict[str, Claim] = {}
        self.relations: list[tuple[str, str, str]] = []
        self.log: list[dict[str, Any]] = []
        if self.path and self.path.exists():
            self._load()

    # ------------------------------------------------------------------ persistence

    def _load(self) -> None:
        assert self.path is not None
        data = json.loads(self.path.read_text())
        self.claims = {c["id"]: Claim.from_dict(c) for c in data.get("claims", [])}
        self.relations = [tuple(r) for r in data.get("relations", [])]
        self.log = list(data.get("log", []))

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "claims": [c.to_dict() for c in self.claims.values()],
            "relations": [list(r) for r in self.relations],
            "log": self.log,
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=1))
        tmp.replace(self.path)

    def _note(self, op: str, claim: Claim, detail: str = "", **extra: Any) -> dict[str, Any]:
        entry = {
            "t": time.time(),
            "op": op,
            "claim": claim.id,
            "family": claim.family,
            "detail": detail,
            **extra,
        }
        self.log.append(entry)
        claim.updated_at = entry["t"]
        return entry

    def link(self, src: str, relation: str, dst: str) -> None:
        if (src, relation, dst) not in self.relations:
            self.relations.append((src, relation, dst))
            if self.store is not None:
                self.store.link(src, relation, dst)

    def _mirror(self, claim: Claim) -> None:
        if self.store is None:
            return
        data = claim.to_dict()
        data.pop("evidence")
        self.store.add_node(claim.id, "claim", label=claim.statement[:120], data=data)

    # ------------------------------------------------------------------ access

    def add(self, claim: Claim, reason: str = "proposed") -> Claim:
        """Add a root claim (a new family) as a hypothesis."""
        if claim.id in self.claims:
            raise ValueError(f"claim {claim.id} already exists")
        self.claims[claim.id] = claim
        self._mirror(claim)
        self._note("propose", claim, reason)
        self.save()
        return claim

    def get(self, claim_id: str) -> Claim:
        return self.claims[claim_id]

    def root(self, claim: Claim | str) -> Claim:
        claim = self.claims[claim] if isinstance(claim, str) else claim
        return self.claims[claim.family]

    def roots(self) -> list[Claim]:
        return [c for c in self.claims.values() if c.is_root]

    def children(self, root_id: str, active_only: bool = True) -> list[Claim]:
        return [
            c
            for c in self.claims.values()
            if c.family == root_id and not c.is_root and (not active_only or c.status != RETIRED)
        ]

    def find_duplicate(self, claim: Claim) -> Claim | None:
        """An existing root making the same comparison (in either direction)."""
        for root in self.roots():
            if root.env_id != claim.env_id or root.metric != claim.metric:
                continue
            same = root.intervention == claim.intervention and root.baseline == claim.baseline
            mirrored = root.intervention == claim.baseline and root.baseline == claim.intervention
            if same or mirrored:
                return root
        return None

    # ------------------------------------------------------------------ evidence

    def record(self, root_id: str, evidence: Evidence) -> list[dict[str, Any]]:
        """Add outcome evidence to a family and revise it. Returns the revision log entries.

        A repeat test at the same point with the same background replaces the earlier
        one (it used more seeds).
        """
        root = self.claims[root_id]
        if not root.is_root:
            raise ValueError("evidence is recorded on the family's root claim")
        if evidence.kind != "outcome":
            raise ValueError("use record_mechanism for mediator and moderator evidence")
        background = evidence.details.get("background")
        root.evidence = [
            e
            for e in root.evidence
            if not (
                e.kind == "outcome"
                and e.conditions == evidence.conditions
                and e.details.get("background") == background
            )
        ]
        root.evidence.append(evidence)
        start = len(self.log)
        self._note(
            "evidence",
            root,
            evidence.summary(),
            experiment=evidence.experiment_id,
            label=evidence.label,
        )
        if self.store is not None:
            self.store.add_node(
                evidence.experiment_id,
                "experiment",
                prov_type="activity",
                label=evidence.summary()[:120],
                data=evidence.details,
            )
            self.store.add_node(
                evidence.id, "evidence", label=evidence.label, data=evidence.to_dict()
            )
            self.store.link(evidence.id, "wasGeneratedBy", evidence.experiment_id)
            if evidence.verdict in (SUPPORTS, CONTRADICTS):
                self.store.link(evidence.id, evidence.verdict, root.id)
        self.revise(root_id)
        self.save()
        return self.log[start:]

    def record_mechanism(self, claim_id: str, index: int, evidence: Evidence) -> dict[str, Any]:
        """Attach mediator or moderator evidence to one of a claim's mechanisms."""
        claim = self.claims[claim_id]
        mechanism = claim.mechanisms[index]
        before = mechanism.status
        mechanism.evidence = [
            e
            for e in mechanism.evidence
            if not (e.kind == evidence.kind and e.conditions == evidence.conditions)
        ]
        mechanism.evidence.append(evidence)
        entry = self._note(
            "mechanism",
            claim,
            f"'{mechanism.statement}': {evidence.summary()} (explanation {before} -> {mechanism.status})",
            experiment=evidence.experiment_id,
            mechanism=index,
        )
        if self.store is not None:
            self.store.add_node(
                evidence.id,
                "evidence",
                label=f"{evidence.kind}:{evidence.verdict}",
                data=evidence.to_dict(),
            )
            if evidence.verdict in (SUPPORTS, CONTRADICTS):
                self.store.link(evidence.id, evidence.verdict, claim.id)
        self._mirror(claim)
        self.save()
        return entry

    # ------------------------------------------------------------------ revision

    @staticmethod
    def _view(evidence: Evidence, polarity: int) -> Evidence:
        """Evidence about the root's comparison, re-read for a claim of the given polarity."""
        if polarity > 0:
            return evidence
        verdict = {B_BETTER: SUPPORTS, A_BETTER: CONTRADICTS, NO_BENEFIT: CONTRADICTS}.get(
            evidence.label, INCONCLUSIVE
        )
        return Evidence(
            experiment_id=evidence.experiment_id,
            kind=evidence.kind,
            verdict=verdict,
            label=evidence.label,
            conditions=dict(evidence.conditions),
            n=evidence.n,
            effect=-evidence.effect,
            ci_low=-evidence.ci_high,
            ci_high=-evidence.ci_low,
            p_value=evidence.p_value,
            details=evidence.details,
            id=evidence.id,
            created_at=evidence.created_at,
        )

    def _polarity(self, claim: Claim) -> int:
        return 1 if claim.intervention == self.root(claim).intervention else -1

    def _set_status(self, claim: Claim, status: str, why: str) -> None:
        if claim.status != status:
            before = claim.status
            claim.status = status
            self._note(
                {
                    SUPPORTED: "support",
                    REFUTED: "refute",
                    CONTESTED: "contest",
                    SUPERSEDED: "supersede",
                    RETIRED: "retire",
                    HYPOTHESIS: "reopen",
                }[status],
                claim,
                f"{before} -> {status}: {why}",
            )
            self._mirror(claim)

    def revise(self, root_id: str) -> None:
        """Bring a family's claims in line with its pooled evidence.

        Statuses are recomputed, and when the evidence disagrees across conditions the
        family is re-partitioned: existing specialised claims are re-scoped, new ones
        are created, and ones the evidence no longer supports are retired.
        """
        root = self.claims[root_id]
        pool = [e for e in root.evidence if e.kind == "outcome"]
        decisive = [e for e in pool if e.label in DECISIVE]
        # Every tested point takes part in the partition, including those that stayed
        # inconclusive: a region where the claim could not be established gets no
        # claim, instead of being covered by whatever its neighbours showed.
        tested = [(dict(e.conditions), e.label) for e in pool]
        leaves = partition(tested, root.scope, self.max_depth) if decisive else []
        labels = {leaf.label for leaf in leaves}

        if not decisive:
            self._set_status(root, HYPOTHESIS, "no decisive evidence yet")
        elif labels == {A_BETTER}:
            self._set_status(root, SUPPORTED, f"{len(decisive)} decisive test(s), all in favour")
        elif A_BETTER in labels or MIXED in labels:
            unresolved_only = labels <= {A_BETTER, INCONCLUSIVE}
            self._set_status(
                root,
                SUPERSEDED,
                "established in only part of its scope; replaced by narrower claims"
                if unresolved_only
                else "evidence disagrees across conditions; replaced by narrower claims",
            )
        else:
            self._set_status(root, REFUTED, f"{len(decisive)} decisive test(s), none in favour")

        wanted: list[tuple[int, Leaf]] = []
        single_supported = labels == {A_BETTER}
        for leaf in leaves:
            if leaf.label == A_BETTER and not single_supported:
                wanted.append((1, leaf))
            elif leaf.label == B_BETTER:
                wanted.append((-1, leaf))
            elif leaf.label == MIXED:
                wanted.append((1, leaf))

        existing = self.children(root_id)
        unmatched = list(existing)
        for polarity, leaf in wanted:
            match = next(
                (
                    c
                    for c in unmatched
                    if self._polarity(c) == polarity and c.scope.intersects(leaf.region)
                ),
                None,
            )
            if match is not None:
                unmatched.remove(match)
                if match.scope.to_dict() != leaf.region.to_dict():
                    before = match.scope.describe()
                    match.scope = leaf.region
                    self._note(
                        "rescope",
                        match,
                        f"scope changed from [{before}] to [{leaf.region.describe()}]",
                    )
                child = match
            else:
                child = self._specialise(root, polarity, leaf)
            child.evidence = [self._view(e, polarity) for e in pool]
            if leaf.label == MIXED:
                self._set_status(
                    child,
                    CONTESTED,
                    f"the {len(leaf.points)} test(s) in its region disagree and could not "
                    "be separated",
                )
            else:
                self._set_status(
                    child, SUPPORTED, f"{len(leaf.points)} decisive test(s) in its region"
                )
            self._mirror(child)
        for stale in unmatched:
            stale.evidence = [self._view(e, self._polarity(stale)) for e in pool]
            self._set_status(
                stale, RETIRED, "its region is no longer supported by the pooled evidence"
            )
        if root.status == SUPERSEDED:
            for child in self.children(root_id):
                self.link(child.id, SUPERSEDES, root.id)
        root.origin["no_benefit_regions"] = [
            leaf.region.describe() for leaf in leaves if leaf.label == NO_BENEFIT
        ]
        root.origin["unresolved_regions"] = [
            leaf.region.describe() for leaf in leaves if leaf.label == INCONCLUSIVE
        ]
        self._mirror(root)

    def _specialise(self, root: Claim, polarity: int, leaf: Leaf) -> Claim:
        if polarity > 0:
            intervention, baseline = root.intervention, root.baseline
            statement = root.statement
        else:
            intervention, baseline = root.baseline, root.intervention
            preferred = ", ".join(f"{p}={v:g}" for p, v in sorted(intervention.items()))
            statement = (
                f"Here the reverse holds: {preferred} does better. "
                f"(Reverses the claim: {root.statement})"
            )
        child = Claim(
            statement=statement,
            intervention=dict(intervention),
            baseline=dict(baseline),
            scope=leaf.region,
            metric=root.metric,
            min_effect=root.min_effect,
            mechanisms=[],
            family=root.id,
            parent=root.id,
            origin={"author": "revision", "from": root.id},
            env_id=root.env_id,
        )
        self.claims[child.id] = child
        self.link(child.id, SPECIALIZES, root.id)
        if polarity < 0:
            self.link(child.id, CONTRADICTS_REL, root.id)
        self._note(
            "specialize",
            child,
            f"{'narrowed' if polarity > 0 else 'reversed'} from {root.id}: {leaf.region.describe()}",
        )
        return child

    # ------------------------------------------------------------------ retrieval

    def active(self, root_id: str) -> list[Claim]:
        """The claims that currently speak for a family: its live children, or the root itself."""
        children = [c for c in self.children(root_id) if c.status in (SUPPORTED, CONTESTED)]
        if children:
            return children
        root = self.claims[root_id]
        return [root] if root.status in (SUPPORTED, HYPOTHESIS, CONTESTED) else []

    def applicable(
        self,
        conditions: dict[str, float],
        statuses: tuple[str, ...] = (SUPPORTED,),
        env_id: str | None = None,
    ) -> list[tuple[Claim, float]]:
        """Claims whose scope contains ``conditions``, with how far the nearest supporting test is.

        The distance (log-ratio units over the variables the family was tested on) is
        zero when the claim was tested exactly here and grows as the claim is being
        extrapolated; callers can use it to tell tested ground from speculation.
        """
        out: list[tuple[Claim, float]] = []
        for root in self.roots():
            if env_id is not None and root.env_id != env_id:
                continue
            for claim in self.active(root.id):
                if claim.status not in statuses or not claim.scope.contains(conditions):
                    continue
                supporting = [e for e in claim.outcome_evidence() if e.verdict == SUPPORTS]
                if supporting:
                    variables = sorted(supporting[0].conditions)
                    distance = min(
                        log_distance(conditions, e.conditions, variables) for e in supporting
                    )
                else:
                    distance = math.inf
                out.append((claim, distance))
        return out

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for claim in self.claims.values():
            by_status[claim.status] = by_status.get(claim.status, 0) + 1
        ops: dict[str, int] = {}
        for entry in self.log:
            ops[entry["op"]] = ops.get(entry["op"], 0) + 1
        return {
            "families": len(self.roots()),
            "claims": len(self.claims),
            "by_status": by_status,
            "relations": len(self.relations),
            "revisions": ops,
        }
