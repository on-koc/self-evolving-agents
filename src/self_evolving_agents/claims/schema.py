"""Claims, their applicability and their evidence.

A claim is a *conditional, comparative* statement about a strategy:

    within <scope>, running the policy with <intervention> instead of <baseline>
    improves <metric> by at least <min_effect>.

It may carry a *mechanism*: a stated reason, expressed as predictions that can be
checked separately from the outcome. This separation is deliberate. A simulator can
confirm that a strategy scored better without confirming the story told about why;
the outcome evidence and the mechanism evidence are therefore stored and judged
independently.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from ..types import jsonable, new_id

# Claim status.
HYPOTHESIS = "hypothesis"  # proposed, not yet decided by controlled evidence
SUPPORTED = "supported"  # every decisive test inside its scope agreed with it
REFUTED = "refuted"  # every decisive test inside its scope disagreed with it
CONTESTED = "contested"  # decisive tests inside its scope disagree with each other
SUPERSEDED = "superseded"  # replaced by more specific claims
RETIRED = "retired"  # withdrawn; kept so its counterexamples stay retrievable
ACTIVE_STATUSES = (HYPOTHESIS, SUPPORTED, REFUTED, CONTESTED)

# What one controlled comparison said about "intervention vs baseline" at one point.
A_BETTER = "intervention_better"
B_BETTER = "baseline_better"
# The claimed gain is ruled out: the interval lies below min_effect. The baseline may be
# as good or slightly better, but not by enough to recommend it either.
NO_BENEFIT = "no_benefit"
# Still undecided after the maximum number of seeds. Treated as "not established here".
INCONCLUSIVE = "inconclusive"
DECISIVE = (A_BETTER, B_BETTER, NO_BENEFIT)

# Verdict of a piece of evidence relative to the claim (or mechanism) it is attached to.
SUPPORTS = "supports"
CONTRADICTS = "contradicts"

Bounds = tuple[float | None, float | None]


@dataclass
class Region:
    """An axis-aligned box in condition space: where a claim is asserted to apply.

    ``bounds[var] = (low, high)`` means ``low <= var < high``; ``None`` leaves that
    side open. Variables not mentioned are unconstrained.
    """

    bounds: dict[str, Bounds] = field(default_factory=dict)

    def contains(self, conditions: dict[str, Any]) -> bool:
        for var, (low, high) in self.bounds.items():
            if var not in conditions:
                return False
            value = float(conditions[var])
            if low is not None and value < low:
                return False
            if high is not None and value >= high:
                return False
        return True

    def restrict(self, var: str, low: float | None = None, high: float | None = None) -> Region:
        """Intersection with ``low <= var < high``."""
        old_low, old_high = self.bounds.get(var, (None, None))
        new_low = old_low if low is None else (low if old_low is None else max(low, old_low))
        new_high = old_high if high is None else (high if old_high is None else min(high, old_high))
        return Region({**self.bounds, var: (new_low, new_high)})

    def intersects(self, other: Region) -> bool:
        """True if the two regions share at least one point."""
        for var in set(self.bounds) | set(other.bounds):
            low_a, high_a = self.bounds.get(var, (None, None))
            low_b, high_b = other.bounds.get(var, (None, None))
            lows = [x for x in (low_a, low_b) if x is not None]
            highs = [x for x in (high_a, high_b) if x is not None]
            if lows and highs and max(lows) >= min(highs):
                return False
        return True

    def is_empty(self) -> bool:
        return any(
            low is not None and high is not None and low >= high
            for low, high in self.bounds.values()
        )

    def within(self, other: Region) -> bool:
        """True if every point of this region lies inside ``other``."""
        for var, (o_low, o_high) in other.bounds.items():
            low, high = self.bounds.get(var, (None, None))
            if o_low is not None and (low is None or low < o_low):
                return False
            if o_high is not None and (high is None or high > o_high):
                return False
        return True

    @property
    def constrained(self) -> list[str]:
        return [v for v, (low, high) in self.bounds.items() if low is not None or high is not None]

    def describe(self) -> str:
        parts = []
        for var in sorted(self.bounds):
            low, high = self.bounds[var]
            if low is None and high is None:
                continue
            if low is not None and high is not None:
                parts.append(f"{low:g} <= {var} < {high:g}")
            elif low is not None:
                parts.append(f"{var} >= {low:g}")
            else:
                parts.append(f"{var} < {high:g}")
        return " and ".join(parts) if parts else "all tested conditions"

    def to_dict(self) -> dict[str, list[float | None]]:
        return {var: [low, high] for var, (low, high) in sorted(self.bounds.items())}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> Region:
        return cls({var: (pair[0], pair[1]) for var, pair in (d or {}).items()})


@dataclass
class Evidence:
    """The result of one controlled comparison, as it bears on one claim.

    ``kind`` says which judgement it informs:

    * ``outcome``   – did the intervention beat the baseline on the claim's metric?
    * ``mediator``  – did the quantity the mechanism says carries the effect move?
    * ``moderator`` – did the effect change with a condition as the mechanism predicts?

    ``effect`` is signed so that positive always means "as predicted".
    """

    experiment_id: str
    kind: str
    verdict: str
    conditions: dict[str, float]
    n: int
    effect: float
    ci_low: float
    ci_high: float
    p_value: float
    label: str = ""  # outcome evidence: A_BETTER / B_BETTER / NO_BENEFIT / INCONCLUSIVE
    details: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("ev"))
    created_at: float = field(default_factory=time.time)

    def summary(self) -> str:
        where = ", ".join(f"{k}={v:g}" for k, v in sorted(self.conditions.items()))
        return (
            f"{self.kind} {self.verdict}: effect {self.effect:+.3f} "
            f"[{self.ci_low:+.3f}, {self.ci_high:+.3f}], n={self.n}, at {where}"
        )

    def to_dict(self) -> dict[str, Any]:
        return jsonable(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Evidence:
        return cls(**d)


@dataclass
class Mechanism:
    """A stated reason for a claim, as checkable predictions.

    * ``mediator`` names an outcome metric through which the effect is said to flow,
      and ``mediator_direction`` the sign of its predicted change (intervention minus
      baseline). ``failure:<mode>`` refers to the rate of that failure mode.
    * ``moderator`` names a condition that should strengthen (+1) or weaken (-1) the
      effect as it increases.

    A mechanism whose mediator does not move cannot be what produced the effect, no
    matter how well the outcome claim is doing.
    """

    statement: str
    mediator: str | None = None
    mediator_direction: int = 0
    moderator: str | None = None
    moderator_direction: int = 0
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def status(self) -> str:
        return _status_from([e.verdict for e in self.evidence])

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "mediator": self.mediator,
            "mediator_direction": self.mediator_direction,
            "moderator": self.moderator,
            "moderator_direction": self.moderator_direction,
            "status": self.status,
            "evidence": [e.to_dict() for e in self.evidence],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Mechanism:
        return cls(
            statement=d["statement"],
            mediator=d.get("mediator"),
            mediator_direction=int(d.get("mediator_direction", 0)),
            moderator=d.get("moderator"),
            moderator_direction=int(d.get("moderator_direction", 0)),
            evidence=[Evidence.from_dict(e) for e in d.get("evidence", [])],
        )


def _status_from(verdicts: list[str]) -> str:
    supports = verdicts.count(SUPPORTS)
    contradicts = verdicts.count(CONTRADICTS)
    if supports and contradicts:
        return CONTESTED
    if supports:
        return SUPPORTED
    if contradicts:
        return REFUTED
    return HYPOTHESIS


@dataclass
class Claim:
    """A conditional strategy claim. See the module docstring for how to read one."""

    statement: str
    intervention: dict[str, float]
    baseline: dict[str, float]
    scope: Region = field(default_factory=Region)
    metric: str = "score"
    min_effect: float = 0.02
    mechanisms: list[Mechanism] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("claim"))
    family: str = ""  # id of the root claim whose comparison this one is a region of
    parent: str | None = None
    status: str = HYPOTHESIS
    origin: dict[str, Any] = field(default_factory=dict)
    env_id: str = "bsk-scan"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if set(self.intervention) != set(self.baseline):
            raise ValueError("intervention and baseline must set the same policy parameters")
        if not self.intervention:
            raise ValueError("a claim must change at least one policy parameter")
        if self.intervention == self.baseline:
            raise ValueError("intervention and baseline are identical")
        if not self.family:
            self.family = self.id

    @property
    def is_root(self) -> bool:
        return self.family == self.id

    @property
    def parameters(self) -> tuple[str, ...]:
        return tuple(sorted(self.intervention))

    def outcome_evidence(self, inside_scope: bool = True) -> list[Evidence]:
        return [
            e
            for e in self.evidence
            if e.kind == "outcome" and (not inside_scope or self.scope.contains(e.conditions))
        ]

    def counterexamples(self) -> list[Evidence]:
        """Decisive tests where this claim's prediction failed, inside or outside its scope."""
        return [e for e in self.evidence if e.kind == "outcome" and e.verdict == CONTRADICTS]

    def evidence_status(self) -> str:
        """Status implied by the outcome evidence inside the scope (ignores superseded/retired)."""
        return _status_from([e.verdict for e in self.outcome_evidence()])

    def tested_range(self, var: str) -> tuple[float, float] | None:
        """Smallest and largest value of ``var`` at which this claim was actually supported."""
        values = [
            e.conditions[var]
            for e in self.outcome_evidence()
            if e.verdict == SUPPORTS and var in e.conditions
        ]
        return (min(values), max(values)) if values else None

    def describe(self) -> str:
        change = ", ".join(
            f"{p}={self.intervention[p]:g} (instead of {self.baseline[p]:g})"
            for p in self.parameters
        )
        return f"[{self.status}] {self.statement} | where: {self.scope.describe()} | do: {change}"

    def to_dict(self) -> dict[str, Any]:
        return jsonable(
            {
                "id": self.id,
                "family": self.family,
                "parent": self.parent,
                "status": self.status,
                "statement": self.statement,
                "scope": self.scope.to_dict(),
                "intervention": self.intervention,
                "baseline": self.baseline,
                "metric": self.metric,
                "min_effect": self.min_effect,
                "mechanisms": [m.to_dict() for m in self.mechanisms],
                "evidence": [e.to_dict() for e in self.evidence],
                "origin": self.origin,
                "env_id": self.env_id,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Claim:
        return cls(
            statement=d["statement"],
            intervention={k: float(v) for k, v in d["intervention"].items()},
            baseline={k: float(v) for k, v in d["baseline"].items()},
            scope=Region.from_dict(d.get("scope")),
            metric=d.get("metric", "score"),
            min_effect=float(d.get("min_effect", 0.02)),
            mechanisms=[Mechanism.from_dict(m) for m in d.get("mechanisms", [])],
            evidence=[Evidence.from_dict(e) for e in d.get("evidence", [])],
            id=d.get("id") or new_id("claim"),
            family=d.get("family", ""),
            parent=d.get("parent"),
            status=d.get("status", HYPOTHESIS),
            origin=dict(d.get("origin") or {}),
            env_id=d.get("env_id", "bsk-scan"),
            created_at=float(d.get("created_at", time.time())),
            updated_at=float(d.get("updated_at", time.time())),
        )


def log_distance(a: dict[str, float], b: dict[str, float], variables: list[str]) -> float:
    """Distance between two condition points over ``variables``, in log-ratio units.

    Positive quantities are compared by ratio, so 50 -> 100 is as far as 100 -> 200.
    """
    total = 0.0
    for var in variables:
        x, y = float(a[var]), float(b[var])
        if x > 0 and y > 0:
            total += math.log(x / y) ** 2
        else:
            total += (x - y) ** 2
    return math.sqrt(total)
