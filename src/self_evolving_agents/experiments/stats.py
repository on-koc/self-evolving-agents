"""Statistics for matched-seed experiments.

Every comparison here is *paired*: arm A and arm B are run on the same seeds, so
each seed contributes one difference and the large seed-to-seed variation (a
different orbit, a different starting charge) cancels out. All resampling is
seeded, so an analysis gives the same numbers every time it is run.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass
class PairedResult:
    """Outcome of comparing two arms on matched seeds.

    ``diff`` is ``mean(a - b)``; the interval is a bootstrap percentile interval for
    that mean; ``p_value`` is from a two-sided sign-flip permutation test of "the
    differences are symmetric about zero".
    """

    n: int
    mean_a: float
    mean_b: float
    diff: float
    ci_low: float
    ci_high: float
    p_value: float
    confidence: float = 0.95

    def to_dict(self) -> dict[str, Any]:
        return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def paired_compare(
    a: Sequence[float],
    b: Sequence[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 5000,
    seed: int = 0,
) -> PairedResult:
    """Compare arm ``a`` with arm ``b``; element ``i`` of each comes from the same seed."""
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if x.shape != y.shape or x.ndim != 1:
        raise ValueError("paired comparison needs two equally long one-dimensional samples")
    if x.size < 2:
        raise ValueError("paired comparison needs at least two pairs")
    d = x - y
    low, high, p = _mean_interval_and_p(d, confidence, n_resamples, seed)
    return PairedResult(
        n=int(d.size),
        mean_a=float(x.mean()),
        mean_b=float(y.mean()),
        diff=float(d.mean()),
        ci_low=low,
        ci_high=high,
        p_value=p,
        confidence=confidence,
    )


def _mean_interval_and_p(
    d: np.ndarray, confidence: float, n_resamples: int, seed: int
) -> tuple[float, float, float]:
    observed = float(d.mean())
    if np.allclose(d, d[0]):
        # No variation between pairs: the interval is a point, and the sign test is exact.
        p = 1.0 if abs(observed) < 1e-15 else float(min(1.0, 2.0 * 0.5**d.size))
        return observed, observed, p
    rng = np.random.default_rng(seed)
    n = d.size
    boot = d[rng.integers(0, n, size=(n_resamples, n))].mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    low, high = np.quantile(boot, [alpha, 1.0 - alpha])
    signs = rng.choice((-1.0, 1.0), size=(n_resamples, n))
    permuted = np.abs((signs * d).mean(axis=1))
    p = (1.0 + float(np.sum(permuted >= abs(observed) - 1e-15))) / (1.0 + n_resamples)
    return float(low), float(high), float(min(p, 1.0))


def interaction_compare(
    effect_high: Sequence[float],
    effect_low: Sequence[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 5000,
    seed: int = 0,
) -> PairedResult:
    """Does a treatment effect differ between two levels of a moderating condition?

    Each argument holds per-seed paired effects (treatment minus control) measured at
    one level of the moderator, on the same seeds. The result describes the
    difference of differences.
    """
    return paired_compare(
        effect_high, effect_low, confidence=confidence, n_resamples=n_resamples, seed=seed
    )


@dataclass
class TrendResult:
    """Monotonic association between a moderator's levels and the effect at each level."""

    levels: list[float]
    effects: list[float]
    rho: float
    p_value: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "levels": self.levels,
            "effects": [round(e, 6) for e in self.effects],
            "rho": round(self.rho, 4),
            "p_value": round(self.p_value, 6),
        }


def _ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(len(values), dtype=float)
    for value in np.unique(values):  # average ranks over ties
        mask = values == value
        ranks[mask] = ranks[mask].mean()
    return ranks


def trend_test(
    levels: Sequence[float], effects: Sequence[float], *, n_resamples: int = 5000, seed: int = 0
) -> TrendResult:
    """Spearman rank correlation with a permutation p-value.

    With only a handful of levels the smallest attainable p-value is large (four
    levels cannot go below 1/12 two-sided), so read this alongside the per-level
    effects and :func:`interaction_compare` rather than on its own.
    """
    x, y = np.asarray(levels, dtype=float), np.asarray(effects, dtype=float)
    if x.size != y.size or x.size < 3:
        raise ValueError("a trend needs at least three (level, effect) pairs")
    rx, ry = _ranks(x), _ranks(y)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return TrendResult(list(map(float, x)), list(map(float, y)), 0.0, 1.0)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_resamples):
        permuted = float(np.corrcoef(rx, rng.permutation(ry))[0, 1])
        hits += abs(permuted) >= abs(rho) - 1e-12
    return TrendResult(
        list(map(float, x)), list(map(float, y)), rho, (1.0 + hits) / (1.0 + n_resamples)
    )


def mean_interval(
    values: Sequence[float], *, confidence: float = 0.95, n_resamples: int = 5000, seed: int = 0
) -> tuple[float, float, float]:
    """Mean of a sample with a bootstrap percentile interval: ``(mean, low, high)``."""
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        raise ValueError("no values")
    if v.size == 1 or np.allclose(v, v[0]):
        return float(v.mean()), float(v.mean()), float(v.mean())
    rng = np.random.default_rng(seed)
    boot = v[rng.integers(0, v.size, size=(n_resamples, v.size))].mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    low, high = np.quantile(boot, [alpha, 1.0 - alpha])
    return float(v.mean()), float(low), float(high)
