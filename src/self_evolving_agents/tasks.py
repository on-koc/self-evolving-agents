"""Building task streams from short descriptions (used by the command line and by protocols)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .envs import DISCOVERY_THEMES, UNIT_TESTS, discoveryworld_task, scan_task
from .types import Task

ORDERS = ("sequential", "interleaved")

#: Names that stand for groups of DiscoveryWorld scenarios on the command line.
SCENARIO_GROUPS = {"themes": DISCOVERY_THEMES, "unit-tests": UNIT_TESTS}


def expand_scenarios(names: Sequence[str]) -> list[str]:
    """Scenario names, with ``themes`` and ``unit-tests`` expanded to their members."""
    out: list[str] = []
    for name in names:
        out.extend(SCENARIO_GROUPS.get(name.strip().lower(), [name]))
    return out


def parse_seeds(text: str) -> list[int]:
    """``"0:5"`` -> 0..4, ``"1,4,9"`` -> those, ``"7"`` -> [7]."""
    seeds: list[int] = []
    for part in str(text).split(","):
        part = part.strip()
        if ":" in part:
            start, stop = part.split(":", 1)
            seeds.extend(range(int(start or 0), int(stop)))
        elif part:
            seeds.append(int(part))
    if not seeds:
        raise ValueError(f"no seeds in {text!r}")
    return seeds


def task_stream(
    env: str,
    seeds: Sequence[int],
    *,
    regimes: Sequence[str] = ("nominal",),
    order: str = "sequential",
    conditions: dict[str, float] | None = None,
    params: dict[str, Any] | None = None,
    scenarios: Sequence[str] = (),
    difficulty: str | Sequence[str] = "Normal",
    max_steps: int | None = None,
) -> list[Task]:
    """An ordered stream of tasks.

    For the scanning environments, one group of tasks per regime; for DiscoveryWorld,
    one group per scenario and difficulty (``difficulty`` may list several, as may
    ``scenarios``, where ``themes`` and ``unit-tests`` stand for their members).
    ``order="sequential"`` finishes one group before the next; ``"interleaved"``
    alternates between groups seed by seed. A DiscoveryWorld task without
    ``max_steps`` gets the paper's step limit for its difficulty.
    """
    if order not in ORDERS:
        raise ValueError(f"order must be one of {ORDERS}")
    if env == "discoveryworld":
        if not scenarios:
            raise ValueError("discoveryworld needs at least one scenario")
        difficulties = [difficulty] if isinstance(difficulty, str) else list(difficulty)
        groups = [
            [discoveryworld_task(s, d, seed=seed, max_steps=max_steps) for seed in seeds]
            for s in expand_scenarios(scenarios)
            for d in difficulties
        ]
    else:
        groups = [
            [
                scan_task(env, regime, seed=seed, conditions=conditions or None, **(params or {}))
                for seed in seeds
            ]
            for regime in regimes
        ]
    if order == "interleaved":
        return [group[i] for i in range(len(seeds)) for group in groups]
    return [task for group in groups for task in group]
