"""Acting on the claim graph: which settings does it recommend under given conditions?

Four ways of using what was learned are provided so that they can be compared:

* ``conditional`` – apply a claim only where its scope says it holds. This is what
  the graph is for.
* ``pooled`` – the best *single* setting given every test in the graph: a comparison
  is adopted if its effect, averaged over all the points it was tested at, is
  positive. It sees the same evidence as ``conditional`` but cannot condition on
  anything, which makes it the fair control for "does conditioning matter?".
* ``flat`` – apply every lesson that held at the reference conditions, everywhere.
  This mimics a memory of unconditional lessons ("a lower charge threshold collects
  more data") with no notion of where they stop being true.
* ``reference`` – ignore the graph and use the untuned reference policy.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any

from ..policies import RulePolicy, scanning_policy
from .graph import ClaimGraph
from .schema import A_BETTER, SUPPORTED, Claim, Region
from .testing import Domain, PolicyFactory

MODES = ("reference", "flat", "pooled", "conditional")


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
    check_nearest: bool = True,
) -> Recommendation:
    """Settings the graph recommends at ``conditions``.

    Within a group of parameters, recommendations are chained: if one supported claim
    says 0.40 beats 0.25 here and another says 0.60 beats 0.40 here, the result is
    0.60. A claim whose baseline is not the current setting does not apply, because
    it says nothing about how its intervention compares with that setting.

    ``max_distance`` (conditional mode) refuses to extrapolate: a claim is skipped
    when its nearest supporting test is farther away than this, in log-ratio units.
    ``check_nearest=False`` applies claims by their scope alone, without requiring the
    nearest test to agree (see ``ClaimGraph.applicable``); it exists for comparison.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    defaults = dict(defaults if defaults is not None else scanning_policy.defaults)
    if mode == "reference":
        return Recommendation({}, [])

    edges: dict[tuple[str, ...], list[tuple[dict[str, float], dict[str, float], Claim, float]]] = {}
    if mode == "conditional":
        applicable = graph.applicable(
            conditions, statuses=(SUPPORTED,), check_nearest=check_nearest
        )
        for claim, distance in applicable:
            if max_distance is not None and distance > max_distance:
                continue
            edges.setdefault(claim.parameters, []).append(
                (claim.baseline, claim.intervention, claim, distance)
            )
    elif mode == "pooled":
        for root in graph.roots():
            tested = [e for e in root.evidence if e.kind == "outcome"]
            if not tested:
                continue
            mean_effect = sum(e.effect for e in tested) / len(tested)
            if mean_effect >= root.min_effect:
                edges.setdefault(root.parameters, []).append(
                    (root.baseline, root.intervention, root, 0.0)
                )
            elif mean_effect <= -root.min_effect:
                # The reverse direction wins on average; that is a recommendation too.
                edges.setdefault(root.parameters, []).append(
                    (root.intervention, root.baseline, root, 0.0)
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
                    if mode in ("flat", "pooled") or distance == float("inf")
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
    check_nearest: bool = True,
) -> tuple[RulePolicy, Recommendation]:
    """Build the rule policy the graph recommends for these conditions."""
    defaults = dict(getattr(policy_factory, "defaults", None) or policy_factory().params)
    rec = recommend(
        graph,
        conditions,
        mode=mode,
        domain=domain,
        defaults=defaults,
        max_distance=max_distance,
        check_nearest=check_nearest,
    )
    return policy_factory(name=mode, **rec.settings), rec


def _inside(low: float | None, high: float | None) -> float:
    """A value inside ``[low, high)``, for either bound possibly open."""
    if low is None and high is None:
        return 1.0
    if low is None:
        assert high is not None
        return high / 1.5 if high > 0 else high - 1.0
    if high is None:
        return low * 1.5 if low > 0 else low + 1.0
    return math.sqrt(low * high) if low > 0 else (low + high) / 2.0


def policy_map(
    graph: ClaimGraph, *, defaults: dict[str, float] | None = None
) -> list[dict[str, Any]]:
    """What the graph recommends in every region of condition space its claims tell apart.

    The bounds of all supported claims cut each condition variable into intervals;
    inside one cell of the resulting grid the same claims apply, so the recommendation
    is evaluated once per cell, at a point inside it. Neighbouring cells along the
    most finely cut variable are merged when they recommend the same settings. A row
    with no settings is where the graph recommends leaving the reference policy alone.
    """
    cuts: dict[str, set[float]] = {}
    for claim in graph.claims.values():
        if claim.status != SUPPORTED:
            continue
        for var, (low, high) in claim.scope.bounds.items():
            cuts.setdefault(var, set()).update(b for b in (low, high) if b is not None)
    # The variable with the most cuts goes last, so that it is the one merged along.
    variables = sorted(cuts, key=lambda var: (len(cuts[var]), var))
    axes: list[list[tuple[float | None, float | None]]] = []
    for var in variables:
        edges = sorted(cuts[var])
        axes.append([(None, edges[0]), *itertools.pairwise(edges), (edges[-1], None)])
    rows: list[dict[str, Any]] = []
    for cell in itertools.product(*axes):
        bounds = dict(zip(variables, cell, strict=True))
        point = {var: _inside(low, high) for var, (low, high) in bounds.items()}
        rec = recommend(graph, point, mode="conditional", defaults=defaults)
        claims = [reason["claim"] for reason in rec.reasons]
        previous = rows[-1] if rows else None
        if previous is not None and variables and previous["settings"] == rec.settings:
            last = variables[-1]
            before, low_high = previous["region"].bounds, bounds[last]
            same_elsewhere = all(before[var] == bounds[var] for var in variables[:-1])
            if same_elsewhere and before[last][1] == low_high[0]:
                previous["region"] = Region({**before, last: (before[last][0], low_high[1])})
                previous["claims"] += [c for c in claims if c not in previous["claims"]]
                continue
        rows.append({"region": Region(bounds), "settings": rec.settings, "claims": claims})
    return rows
