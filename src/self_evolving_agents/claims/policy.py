"""Acting on the claim graph: which settings does it recommend under given conditions?

Three ways of using what was learned are provided so that they can be compared:

* ``conditional`` – apply a claim only where its scope says it holds. This is what
  the graph is for.
* ``flat`` – apply every lesson that held at the reference conditions, everywhere.
  This mimics a memory of unconditional lessons ("a lower charge threshold collects
  more data") with no notion of where they stop being true.
* ``reference`` – ignore the graph and use the untuned reference policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..policies import RulePolicy, scanning_policy
from .graph import ClaimGraph
from .schema import A_BETTER, SUPPORTED, Claim
from .testing import Domain, PolicyFactory

MODES = ("conditional", "flat", "reference")


@dataclass
class Recommendation:
    """Parameter settings for one set of conditions, and the claims that justify them."""

    settings: dict[str, float]
    reasons: list[dict[str, Any]]


def _follow(
    start: dict[str, float], edges: list[tuple[dict[str, float], dict[str, float], Claim, float]]
) -> tuple[dict[str, float], list[tuple[Claim, float]]]:
    """Follow "this setting beats that one" edges from the starting setting until none applies."""
    current, used, seen = dict(start), [], [dict(start)]
    while True:
        step = next((e for e in edges if e[0] == current), None)
        if step is None or step[1] in seen:
            return current, used
        current = dict(step[1])
        seen.append(current)
        used.append((step[2], step[3]))


def recommend(
    graph: ClaimGraph,
    conditions: dict[str, float],
    *,
    mode: str = "conditional",
    domain: Domain | None = None,
    defaults: dict[str, float] | None = None,
    max_distance: float | None = None,
) -> Recommendation:
    """Settings the graph recommends at ``conditions``.

    Within a group of parameters, recommendations are chained: if one supported claim
    says 0.40 beats 0.25 here and another says 0.60 beats 0.40 here, the result is
    0.60. A claim whose baseline is not the current setting does not apply, because
    it says nothing about how its intervention compares with that setting.

    ``max_distance`` (conditional mode) refuses to extrapolate: a claim is skipped
    when its nearest supporting test is farther away than this, in log-ratio units.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    defaults = dict(defaults if defaults is not None else scanning_policy.defaults)
    if mode == "reference":
        return Recommendation({}, [])

    edges: dict[tuple[str, ...], list[tuple[dict[str, float], dict[str, float], Claim, float]]] = {}
    if mode == "conditional":
        for claim, distance in graph.applicable(conditions, statuses=(SUPPORTED,)):
            if max_distance is not None and distance > max_distance:
                continue
            edges.setdefault(claim.parameters, []).append(
                (claim.baseline, claim.intervention, claim, distance)
            )
    else:  # flat
        anchor = domain.explored(domain.anchor()) if domain is not None else None
        for root in graph.roots():
            at_anchor = [
                e
                for e in root.evidence
                if e.kind == "outcome" and (anchor is None or e.conditions == anchor)
            ]
            if at_anchor and all(e.label == A_BETTER for e in at_anchor):
                edges.setdefault(root.parameters, []).append(
                    (root.baseline, root.intervention, root, 0.0)
                )

    settings: dict[str, float] = {}
    reasons: list[dict[str, Any]] = []
    for group, group_edges in edges.items():
        start = {p: defaults[p] for p in group}
        # Prefer the claim that is on firmer ground when several start from the same setting.
        group_edges.sort(key=lambda e: e[3])
        final, used = _follow(start, group_edges)
        if final != start:
            settings.update(final)
        for claim, distance in used:
            reasons.append(
                {
                    "claim": claim.id,
                    "statement": claim.statement,
                    "set": claim.intervention,
                    # None: not established for these conditions at all (flat mode, or untested).
                    "nearest_support_distance": None
                    if mode == "flat" or distance == float("inf")
                    else round(distance, 3),
                }
            )
    return Recommendation(settings, reasons)


def assemble_policy(
    graph: ClaimGraph,
    conditions: dict[str, float],
    *,
    mode: str = "conditional",
    domain: Domain | None = None,
    policy_factory: PolicyFactory = scanning_policy,
    max_distance: float | None = None,
) -> tuple[RulePolicy, Recommendation]:
    """Build the rule policy the graph recommends for these conditions."""
    defaults = dict(getattr(policy_factory, "defaults", None) or policy_factory().params)
    rec = recommend(
        graph, conditions, mode=mode, domain=domain, defaults=defaults, max_distance=max_distance
    )
    return policy_factory(name=mode, **rec.settings), rec
