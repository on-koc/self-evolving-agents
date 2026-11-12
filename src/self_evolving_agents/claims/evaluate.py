"""Does what the graph learned carry over to conditions it was never tested under?

The comparison is between ways of *using* the same evidence:

* ``reference``   – the untuned policy; the floor.
* ``flat``        – every lesson that held at the reference conditions, applied
  everywhere. This is what a store of unconditional lessons amounts to.
* ``pooled``      – the best single setting given every test in the graph. Same
  evidence as ``conditional``, no conditioning: the control for whether the
  conditions matter.
* ``conditional`` – the claim graph: a lesson is applied only inside its scope.
* ``oracle``      – optional ceiling: for each test point, the best of a candidate set
  of settings, chosen on separate tuning seeds.

All methods are run on the same held-out seeds at the same held-out points, so the
differences between them are paired.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import Any

import numpy as np

from ..experiments import EpisodeRunner, EpisodeSpec, paired_compare
from ..policies import scanning_policy
from .graph import ClaimGraph
from .policy import MODES, recommend
from .testing import Domain, PolicyFactory


def _run(
    runner: EpisodeRunner,
    domain: Domain,
    policy_factory: PolicyFactory,
    conditions: dict[str, float],
    settings: dict[str, float],
    seeds: Sequence[int],
) -> list[Any]:
    policy = policy_factory(**settings)
    return runner.run([EpisodeSpec(domain.task(conditions, s), policy) for s in seeds])


def evaluate_transfer(
    runner: EpisodeRunner,
    graph: ClaimGraph,
    domain: Domain,
    test_points: Sequence[dict[str, float]],
    seeds: Sequence[int],
    *,
    modes: Sequence[str] = MODES,
    policy_factory: PolicyFactory = scanning_policy,
    oracle_grid: dict[str, list[float]] | None = None,
    tuning_seeds: Sequence[int] | None = None,
    max_distance: float | None = None,
) -> dict[str, Any]:
    """Evaluate each way of using the graph at held-out points.

    Args:
        test_points: explored-variable values of each held-out point.
        seeds: evaluation seeds; must not overlap the seeds the study experimented on.
        oracle_grid: if given, parameter values whose cartesian product forms the
            oracle's candidate settings.
        tuning_seeds: seeds on which the oracle picks its setting (disjoint from ``seeds``).
    """
    defaults = dict(getattr(policy_factory, "defaults", None) or policy_factory().params)
    methods = list(modes) + (["oracle"] if oracle_grid else [])
    scores: dict[str, list[float]] = {m: [] for m in methods}
    failed: dict[str, list[float]] = {m: [] for m in methods}
    per_point: list[dict[str, Any]] = []

    for point in test_points:
        conditions = domain.conditions(**point)
        row: dict[str, Any] = {"conditions": dict(point), "methods": {}}
        for mode in modes:
            rec = recommend(
                graph,
                conditions,
                mode=mode,
                domain=domain,
                defaults=defaults,
                max_distance=max_distance if mode == "conditional" else None,
            )
            outcomes = _run(runner, domain, policy_factory, conditions, rec.settings, seeds)
            row["methods"][mode] = _summarise(outcomes, rec.settings, rec.reasons)
            scores[mode] += [o.score for o in outcomes]
            failed[mode] += [float(o.failure is not None) for o in outcomes]
        if oracle_grid:
            if not tuning_seeds:
                raise ValueError("the oracle needs tuning_seeds")
            names = sorted(oracle_grid)
            best_settings, best_mean = {}, -np.inf
            for combo in itertools.product(*(oracle_grid[n] for n in names)):
                settings = dict(zip(names, combo, strict=True))
                tuned = _run(runner, domain, policy_factory, conditions, settings, tuning_seeds)
                mean = float(np.mean([o.score for o in tuned]))
                if mean > best_mean:
                    best_settings, best_mean = settings, mean
            outcomes = _run(runner, domain, policy_factory, conditions, best_settings, seeds)
            row["methods"]["oracle"] = _summarise(outcomes, best_settings, [])
            scores["oracle"] += [o.score for o in outcomes]
            failed["oracle"] += [float(o.failure is not None) for o in outcomes]
        per_point.append(row)

    overall = {
        m: {
            "mean_score": round(float(np.mean(scores[m])), 4),
            "failure_rate": round(float(np.mean(failed[m])), 4),
            "episodes": len(scores[m]),
        }
        for m in methods
    }
    comparisons = {}
    for a, b in (
        ("conditional", "pooled"),
        ("conditional", "flat"),
        ("conditional", "reference"),
        ("pooled", "reference"),
        ("flat", "reference"),
        ("oracle", "conditional"),
    ):
        if a in scores and b in scores:
            comparisons[f"{a}_minus_{b}"] = {
                "score": paired_compare(scores[a], scores[b]).to_dict(),
                "failure_rate": paired_compare(failed[a], failed[b]).to_dict(),
            }
    return {
        "test_points": [dict(p) for p in test_points],
        "seeds": [int(seeds[0]), int(seeds[-1])],
        "n_seeds": len(seeds),
        "overall": overall,
        "comparisons": comparisons,
        "per_point": per_point,
    }


def _summarise(
    outcomes: list[Any], settings: dict[str, float], reasons: list[dict[str, Any]]
) -> dict[str, Any]:
    failures: dict[str, int] = {}
    for o in outcomes:
        if o.failure:
            failures[o.failure] = failures.get(o.failure, 0) + 1
    return {
        "mean_score": round(float(np.mean([o.score for o in outcomes])), 4),
        "failure_rate": round(float(np.mean([o.failure is not None for o in outcomes])), 4),
        "failures": failures,
        "settings": settings,
        "claims_applied": [r["claim"] for r in reasons],
    }


def composition_check(
    runner: EpisodeRunner,
    graph: ClaimGraph,
    domain: Domain,
    points: Sequence[dict[str, float]],
    seeds: Sequence[int],
    *,
    policy_factory: PolicyFactory = scanning_policy,
) -> list[dict[str, Any]]:
    """Check that settings supported one at a time still help when applied together.

    Each family was tested against the reference policy with only its own change. At
    every given point this compares the fully assembled policy with the reference on
    matched seeds, and with the best single recommended change, so that an
    interaction between claims shows up as a combined policy that underperforms its
    own parts.
    """
    defaults = dict(getattr(policy_factory, "defaults", None) or policy_factory().params)
    out = []
    for point in points:
        conditions = domain.conditions(**point)
        rec = recommend(graph, conditions, mode="conditional", domain=domain, defaults=defaults)
        row: dict[str, Any] = {"conditions": dict(point), "settings": rec.settings}
        if not rec.settings:
            row["note"] = "no supported claim applies here"
            out.append(row)
            continue
        reference = [o.score for o in _run(runner, domain, policy_factory, conditions, {}, seeds)]
        combined = [
            o.score for o in _run(runner, domain, policy_factory, conditions, rec.settings, seeds)
        ]
        row["combined_minus_reference"] = paired_compare(combined, reference).to_dict()
        singles = {}
        groups: dict[tuple[str, ...], dict[str, float]] = {}
        for reason in rec.reasons:
            groups.setdefault(tuple(sorted(reason["set"])), {}).update(
                {k: rec.settings[k] for k in reason["set"]}
            )
        for group, settings in groups.items():
            single = [
                o.score for o in _run(runner, domain, policy_factory, conditions, settings, seeds)
            ]
            singles[",".join(group)] = round(float(np.mean(single)), 4)
        row["single_change_means"] = singles
        row["combined_mean"] = round(float(np.mean(combined)), 4)
        row["reference_mean"] = round(float(np.mean(reference)), 4)
        if singles:
            best = max(singles.values())
            row["interaction"] = (
                "negative" if row["combined_mean"] < best - 0.01 else "none detected"
            )
        out.append(row)
    return out
