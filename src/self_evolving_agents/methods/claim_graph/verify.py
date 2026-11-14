"""Checking that a study comes out the same when it is run again.

A study is deterministic: the seeds fix the simulator and the resampling, so two runs
of one configuration make the same experiments and reach the same claims. Two things
differ between runs by design and must not count as differences: identifiers of
claims, evidence and experiments are random, and timings depend on the machine and on
what the episode cache already held.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

_ID = re.compile(r"\b(claim|ev|xp)_[0-9a-f]{12}\b")

#: Fields that record when or how fast something ran, or what the cache already held.
VOLATILE = frozenset(
    {
        "t",
        "created_at",
        "updated_at",
        "wall_s",
        "simulation_core_s",
        "evaluation_core_s",
        "evaluation_wall_s",
        "episodes_simulated",
        "episodes_total",
    }
)

#: The files that make up a study's result.
FILES = (
    "config.json",
    "study.json",
    "experiments.jsonl",
    "graph.json",
    "transfer.json",
    "composition.json",
)


def canonical_text(text: str) -> str:
    """Replace every random identifier by its kind and order of first appearance."""
    names: dict[str, str] = {}

    def rename(match: re.Match[str]) -> str:
        return names.setdefault(match.group(0), f"{match.group(1)}#{len(names) + 1}")

    return _ID.sub(rename, text)


def _strip(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def canonical_file(path: Path) -> Any:
    """A result file with identifiers renamed in order of appearance and timings removed."""
    text = canonical_text(path.read_text())
    if path.suffix == ".jsonl":
        return [_strip(json.loads(line)) for line in text.splitlines() if line.strip()]
    return _strip(json.loads(text))


def differences(
    a: Any, b: Any, tolerance: float = 0.0, where: str = "", limit: int = 5
) -> list[str]:
    """Where two canonical values differ: at most ``limit`` locations, as readable paths."""
    out: list[str] = []

    def walk(x: Any, y: Any, path: str) -> None:
        if len(out) >= limit:
            return
        numbers = (int, float)
        if (
            isinstance(x, numbers)
            and isinstance(y, numbers)
            and not isinstance(x, bool)
            and not isinstance(y, bool)
        ):
            if not math.isclose(x, y, rel_tol=0.0, abs_tol=tolerance):
                out.append(f"{path or '(top)'}: {x!r} != {y!r}")
        elif isinstance(x, dict) and isinstance(y, dict):
            for key in list(dict.fromkeys([*x, *y])):
                if key not in x or key not in y:
                    side = "second" if key not in x else "first"
                    out.append(f"{path}.{key}: only in the {side} run")
                else:
                    walk(x[key], y[key], f"{path}.{key}")
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                out.append(f"{path or '(top)'}: {len(x)} entries != {len(y)} entries")
                return
            for i, (xi, yi) in enumerate(zip(x, y, strict=True)):
                walk(xi, yi, f"{path}[{i}]")
        elif x != y:
            out.append(f"{path or '(top)'}: {str(x)[:80]!r} != {str(y)[:80]!r}")

    walk(a, b, where)
    return out[:limit]


def verify_runs(
    run_a: Path, run_b: Path, *, tolerance: float = 0.0, files: tuple[str, ...] = FILES
) -> dict[str, list[str] | None]:
    """Compare two runs of a study file by file.

    Returns, per file: ``[]`` if the runs agree, a list of locations if they differ,
    and ``None`` if neither run has the file (a study run without an evaluation has
    no ``transfer.json``).
    """
    result: dict[str, list[str] | None] = {}
    for name in files:
        path_a, path_b = run_a / name, run_b / name
        if not path_a.exists() and not path_b.exists():
            result[name] = None
        elif not path_a.exists() or not path_b.exists():
            missing = run_a if not path_a.exists() else run_b
            result[name] = [f"missing in {missing}"]
        else:
            result[name] = differences(
                canonical_file(path_a), canonical_file(path_b), tolerance=tolerance
            )
    return result
