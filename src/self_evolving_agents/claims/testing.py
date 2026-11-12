"""Turning claims into controlled experiments, and experiments into evidence.

An experiment here is always an A/B comparison of two rule policies on the *same
seeds* under the *same conditions*: only the parameters named by the claim differ
between the arms. Because a seed fixes the orbit, the epoch and every initial
state, the per-seed difference isolates the effect of the change.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..envs.scanning import DEFAULT_CONDITIONS, scan_task
from ..experiments import EpisodeRunner, EpisodeSpec, paired_compare, trend_test
from ..policies import RulePolicy, scanning_policy
from ..types import Outcome, Task, new_id
from .schema import (
    A_BETTER,
    B_BETTER,
    CONTRADICTS,
    INCONCLUSIVE,
    NO_BENEFIT,
    SUPPORTS,
    Claim,
    Evidence,
    Mechanism,
)

PolicyFactory = Callable[..., RulePolicy]

# Pocock nominal significance levels for a group-sequential design with k equally
# spaced looks and an overall two-sided level of 0.05. Looking at the data several
# times and stopping at the first decisive look would otherwise inflate the rate of
# false findings.
_POCOCK_ALPHA = {1: 0.05, 2: 0.0294, 3: 0.0221, 4: 0.0182, 5: 0.0158}


@dataclass
class Domain:
    """The part of condition space a study is allowed to experiment in.

    ``variables`` maps each explored condition to the levels that may be tested;
    ``fixed`` overrides other conditions for the whole study; everything else keeps
    the environment's reference value.
    """

    variables: dict[str, list[float]]
    env_id: str = "bsk-scan"
    fixed: dict[str, float] = field(default_factory=dict)
    params: dict[str, float] = field(default_factory=dict)
    reference: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CONDITIONS))

    def __post_init__(self) -> None:
        self.variables = {
            v: sorted(float(x) for x in levels) for v, levels in self.variables.items()
        }

    def conditions(self, **values: float) -> dict[str, float]:
        """Complete condition dictionary for a point given by some explored variables."""
        unknown = set(values) - set(self.reference)
        if unknown:
            raise KeyError(f"unknown condition(s): {', '.join(sorted(unknown))}")
        return {**self.reference, **self.fixed, **{k: float(v) for k, v in values.items()}}

    def anchor(self) -> dict[str, float]:
        """The reference point: explored variables at their reference values."""
        return self.conditions()

    def explored(self, conditions: dict[str, float]) -> dict[str, float]:
        return {v: float(conditions[v]) for v in self.variables}

    def grid(self) -> list[dict[str, float]]:
        names = list(self.variables)
        return [
            self.conditions(**dict(zip(names, combo, strict=True)))
            for combo in itertools.product(*(self.variables[n] for n in names))
        ]

    def task(self, conditions: dict[str, float], seed: int) -> Task:
        return scan_task(self.env_id, seed=seed, conditions=conditions, **self.params)

    def to_dict(self) -> dict[str, Any]:
        return {
            "env_id": self.env_id,
            "variables": self.variables,
            "fixed": self.fixed,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Domain:
        return cls(
            variables=d["variables"],
            env_id=d.get("env_id", "bsk-scan"),
            fixed=dict(d.get("fixed") or {}),
            params=dict(d.get("params") or {}),
        )


@dataclass
class ABResult:
    """Raw outcome of one A/B comparison: both arms, seed by seed."""

    conditions: dict[str, float]
    treatment_params: dict[str, float]
    control_params: dict[str, float]
    seeds: list[int]
    treatment: list[Outcome]
    control: list[Outcome]
    id: str = field(default_factory=lambda: new_id("xp"))

    def values(self, metric: str, arm: str) -> np.ndarray:
        outcomes = self.treatment if arm == "treatment" else self.control
        return np.array([metric_value(o, metric) for o in outcomes], dtype=float)

    def summary(self) -> dict[str, Any]:
        def arm(outcomes: list[Outcome]) -> dict[str, Any]:
            failures: dict[str, int] = {}
            for o in outcomes:
                if o.failure:
                    failures[o.failure] = failures.get(o.failure, 0) + 1
            return {
                "mean_score": round(float(np.mean([o.score for o in outcomes])), 5),
                "failures": failures,
            }

        return {
            "n": len(self.seeds),
            "seeds": [self.seeds[0], self.seeds[-1]],
            "treatment": arm(self.treatment),
            "control": arm(self.control),
            "treatment_params": self.treatment_params,
            "control_params": self.control_params,
        }


def metric_value(outcome: Outcome, metric: str) -> float:
    """Read a metric from an outcome. ``failure:<mode>`` is 1 if the episode failed that way."""
    if metric == "score":
        return float(outcome.score)
    if metric == "failure":
        return float(outcome.failure is not None)
    if metric.startswith("failure:"):
        return float(outcome.failure == metric.split(":", 1)[1])
    if metric not in outcome.metrics:
        raise KeyError(f"metric {metric!r} is not reported by this environment")
    return float(outcome.metrics[metric])


def classify_effect(low: float, high: float, mean: float, min_effect: float) -> str:
    """Reading of an interval for "intervention minus baseline" against a claimed gain.

    A claim asserts a gain of at least ``min_effect``. The interval can show that gain
    (``A_BETTER``), show a loss of at least that size (``B_BETTER``), rule the claimed
    gain out without establishing a loss (``NO_BENEFIT``: the whole interval lies below
    ``min_effect``), or leave the question open (``INCONCLUSIVE``).
    """
    if low > 0 and mean >= min_effect:
        return A_BETTER
    if high < 0 and mean <= -min_effect:
        return B_BETTER
    if high < min_effect:
        return NO_BENEFIT
    return INCONCLUSIVE


class ClaimTester:
    """Runs A/B experiments for claims and converts the results into evidence.

    Seeds are added in batches until the comparison is decisive or ``max_seeds`` is
    reached. The confidence level of each look is tightened (Pocock) so that the
    overall chance of a false finding stays near 5% despite the repeated looks.
    """

    def __init__(
        self,
        runner: EpisodeRunner,
        domain: Domain,
        *,
        policy_factory: PolicyFactory = scanning_policy,
        batch: int = 16,
        max_seeds: int = 48,
        seed_base: int = 1000,
    ):
        if batch < 4 or max_seeds < batch:
            raise ValueError("need batch >= 4 and max_seeds >= batch")
        self.runner = runner
        self.domain = domain
        self.policy_factory = policy_factory
        self.batch = batch
        self.max_seeds = max_seeds
        self.seed_base = seed_base
        looks = min(max(math.ceil(max_seeds / batch), 1), 5)
        self.confidence = 1.0 - _POCOCK_ALPHA[looks]
        self.min_complete_pairs = 6
        # Different episodes the experiments have needed, and how many of those had
        # to be simulated now rather than read from the cache.
        self.episodes = 0
        self.simulated = 0

    # ------------------------------------------------------------------ running

    def run_ab(
        self,
        conditions: dict[str, float],
        treatment: dict[str, float],
        control: dict[str, float],
        n_seeds: int,
    ) -> ABResult:
        """Run both arms on the first ``n_seeds`` study seeds (cached episodes are reused)."""
        seeds = list(range(self.seed_base, self.seed_base + n_seeds))
        policy_t = self.policy_factory(**treatment)
        policy_c = self.policy_factory(**control)
        specs = [EpisodeSpec(self.domain.task(conditions, s), policy_t) for s in seeds]
        specs += [EpisodeSpec(self.domain.task(conditions, s), policy_c) for s in seeds]
        needed, simulated = self.runner.episodes_distinct, self.runner.episodes_run
        outcomes = self.runner.run(specs)
        self.episodes += self.runner.episodes_distinct - needed
        self.simulated += self.runner.episodes_run - simulated
        return ABResult(
            conditions=dict(conditions),
            treatment_params=dict(policy_t.params),
            control_params=dict(policy_c.params),
            seeds=seeds,
            treatment=outcomes[: len(seeds)],
            control=outcomes[len(seeds) :],
        )

    def test_claim_at(
        self,
        claim: Claim,
        conditions: dict[str, float],
        background: dict[str, float] | None = None,
    ) -> tuple[ABResult, Evidence]:
        """Sequentially test a claim's comparison at one point of condition space.

        ``background`` holds the other policy parameters, identical in both arms.
        """
        background = dict(background or {})
        treatment = {**background, **claim.intervention}
        control = {**background, **claim.baseline}
        n = self.batch
        while True:
            ab = self.run_ab(conditions, treatment, control, n)
            evidence = self.outcome_evidence(claim, ab)
            if evidence.label != INCONCLUSIVE or n >= self.max_seeds:
                evidence.details["background"] = background
                return ab, evidence
            n = min(n + self.batch, self.max_seeds)

    # ------------------------------------------------------------------ judging

    def outcome_evidence(self, claim: Claim, ab: ABResult) -> Evidence:
        """Did the intervention beat the baseline on the claim's metric at this point?"""
        result = paired_compare(
            ab.values(claim.metric, "treatment"),
            ab.values(claim.metric, "control"),
            confidence=self.confidence,
        )
        label = classify_effect(result.ci_low, result.ci_high, result.diff, claim.min_effect)
        verdict = {A_BETTER: SUPPORTS, B_BETTER: CONTRADICTS, NO_BENEFIT: CONTRADICTS}.get(
            label, INCONCLUSIVE
        )
        return Evidence(
            experiment_id=ab.id,
            kind="outcome",
            verdict=verdict,
            label=label,
            conditions=self.domain.explored(ab.conditions),
            n=result.n,
            effect=result.diff,
            ci_low=result.ci_low,
            ci_high=result.ci_high,
            p_value=result.p_value,
            details={
                **ab.summary(),
                "confidence": round(self.confidence, 4),
                "metric": claim.metric,
            },
        )

    def mediator_evidence(self, mechanism: Mechanism, ab: ABResult) -> Evidence | None:
        """Did the mediator move the way the mechanism says, in an experiment where the effect appeared?

        A mediator that is identical in both arms for every seed contradicts the
        mechanism outright: whatever produced the effect, it was not this.

        Quantities that accumulate over an episode (time spent charging, mode
        switches) are compared only on seeds where *both* arms ran to the time limit.
        Otherwise an arm that loses the spacecraft early would show "less charging"
        merely because its episodes were shorter. Failure-rate mediators use every
        seed, since failing is the thing being measured.
        """
        if not mechanism.mediator or not mechanism.mediator_direction:
            return None
        treated = ab.values(mechanism.mediator, "treatment")
        control = ab.values(mechanism.mediator, "control")
        total = len(treated)
        if not mechanism.mediator.startswith("failure"):
            complete = np.array(
                [
                    t.failure is None and c.failure is None
                    for t, c in zip(ab.treatment, ab.control, strict=True)
                ]
            )
            treated, control = treated[complete], control[complete]
        conditions = self.domain.explored(ab.conditions)
        details: dict[str, Any] = {
            "mediator": mechanism.mediator,
            "pairs_used": int(len(treated)),
            "pairs_total": total,
        }
        if len(treated) < self.min_complete_pairs:
            details.update(treatment_mean=None, control_mean=None, unmoved=False)
            details["note"] = "too few seeds on which both arms completed the episode"
            return Evidence(
                experiment_id=ab.id,
                kind="mediator",
                verdict=INCONCLUSIVE,
                conditions=conditions,
                n=int(len(treated)),
                effect=0.0,
                ci_low=0.0,
                ci_high=0.0,
                p_value=1.0,
                details=details,
            )
        result = paired_compare(treated, control, confidence=self.confidence)
        sign = 1.0 if mechanism.mediator_direction > 0 else -1.0
        effect = sign * result.diff
        low, high = sorted((sign * result.ci_low, sign * result.ci_high))
        unmoved = bool(np.all(treated == control))
        if low > 0:
            verdict = SUPPORTS
        elif unmoved or high < 0:
            verdict = CONTRADICTS
        else:
            verdict = INCONCLUSIVE
        details.update(
            treatment_mean=round(result.mean_a, 5),
            control_mean=round(result.mean_b, 5),
            unmoved=unmoved,
        )
        return Evidence(
            experiment_id=ab.id,
            kind="mediator",
            verdict=verdict,
            conditions=conditions,
            n=result.n,
            effect=effect,
            ci_low=low,
            ci_high=high,
            p_value=result.p_value,
            details=details,
        )

    def moderator_evidence(
        self, claim: Claim, mechanism: Mechanism, by_level: dict[float, ABResult]
    ) -> Evidence | None:
        """Does the effect change with the moderator as the mechanism predicts?

        ``by_level`` holds A/B results at several levels of the moderator, all on the
        same seeds and otherwise identical conditions. The test contrasts the effect
        at the highest and lowest level seed by seed.
        """
        if not mechanism.moderator or not mechanism.moderator_direction or len(by_level) < 2:
            return None
        levels = sorted(by_level)
        n = min(len(by_level[level].seeds) for level in levels)

        def effects(level: float) -> np.ndarray:
            ab = by_level[level]
            return (ab.values(claim.metric, "treatment") - ab.values(claim.metric, "control"))[:n]

        low_level, high_level = levels[0], levels[-1]
        result = paired_compare(effects(high_level), effects(low_level), confidence=self.confidence)
        sign = 1.0 if mechanism.moderator_direction > 0 else -1.0
        effect = sign * result.diff
        low, high = sorted((sign * result.ci_low, sign * result.ci_high))
        if low > 0:
            verdict = SUPPORTS
        elif high < 0 or (low > -claim.min_effect and high < claim.min_effect):
            verdict = CONTRADICTS  # opposite to the prediction, or no moderation at all
        else:
            verdict = INCONCLUSIVE
        per_level = [float(effects(level).mean()) for level in levels]
        details: dict[str, Any] = {
            "moderator": mechanism.moderator,
            "levels": levels,
            "effect_by_level": [round(e, 5) for e in per_level],
        }
        if len(levels) >= 3:
            details["trend"] = trend_test(levels, per_level).to_dict()
        base = by_level[low_level]
        return Evidence(
            experiment_id="+".join(by_level[level].id for level in levels),
            kind="moderator",
            verdict=verdict,
            conditions={
                k: v
                for k, v in self.domain.explored(base.conditions).items()
                if k != mechanism.moderator
            },
            n=n,
            effect=effect,
            ci_low=low,
            ci_high=high,
            p_value=result.p_value,
            details=details,
        )
