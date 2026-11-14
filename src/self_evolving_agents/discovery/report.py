"""Tables of the DiscoveryWorld memory experiment.

Every number is computed from the recorded episodes, the action detectors and, where
present, the grades. Comparisons are paired: two arms are compared on the same world
at the same position of the same phase, with repeats averaged per world first.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ..envs import answer_key
from ..experiments import mean_interval, paired_compare
from .behaviours import detect
from .experiment import episodes, world_of_record, world_tasks

#: Per-episode values that the tables summarise, in display order.
OUTCOMES = ("completion", "progress", "knowledge", "stale", "steps")
BEHAVIOURS = (
    "alternatives",
    "confounds",
    "revision",
    "controls",
    "premature_commit",
    "repeated_measurements",
    "first_test_old_answer",
    "cited_strategy",
)
CODED = ("control", "alternatives", "confound", "revision", "premature_commitment")


def _substances(text: str) -> frozenset[str]:
    return frozenset(re.findall(r"Substance ([A-Z])", text))


def _chemistry_answer(world: dict[str, Any]) -> frozenset[str]:
    key = answer_key(world["scenario"], world["difficulty"], int(world["seed"]))
    return _substances(" ".join(h for task in key for h in task["critical_hypotheses"]))


def _strategy_texts(run: str) -> dict[str, str]:
    """Statements of the strategies an arm's frozen memory holds, by id."""
    path = Path(run).parent / "experience" / "investigation_memory.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {s["id"]: s["statement"] for s in data.get("strategies", [])}


def _cited(traj: Any, texts: dict[str, str]) -> bool | None:
    shown = [d for d in traj.meta.get("retrieval", []) if d.get("kind") == "strategy"]
    if not shown:
        return None
    words = {
        d["label"]: set(re.findall(r"[a-z]{4,}", texts.get(d["id"], "").lower())) for d in shown
    }
    for step in traj.steps:
        thought = (step.thought or "").lower()
        if any(re.search(rf"\b{label.lower()}\b", thought) for label in words):
            return True
        tokens = set(re.findall(r"[a-z]{4,}", thought))
        for vocab in words.values():
            if vocab and len(vocab & tokens) / len(vocab) >= 0.6:
                return True
    return False


def collect(out: str | Path) -> list[dict[str, Any]]:
    """One row per episode: where it sits in the design and every measured value."""
    out = Path(out)
    protocol = json.loads((out / "protocol.json").read_text())
    grades: dict[str, dict[str, Any]] = {}
    path = out / "grades.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                grades[row["key"]] = row  # the last grade of an episode wins
    experience_worlds = [
        world_of_record(t.to_dict())
        for t in world_tasks(protocol["experience"]["worlds"], int(protocol.get("max_steps", 100)))
    ]
    strategies: dict[str, dict[str, str]] = {}
    rows = []
    for episode in episodes(out):
        traj = episode["trajectory"]
        record = episode["record"]
        found = detect(traj) if traj is not None else {}
        grade = grades.get(episode["key"], {})
        row: dict[str, Any] = {
            "key": episode["key"],
            "arm": episode["arm"],
            "method": episode["method"],
            "repeat": episode["repeat"],
            "phase": episode["phase"],
            "condition": episode["condition"],
            "position": episode["position"],
            "world": episode["world"],
            "stand_in": episode["stand_in"],
            "completion": float(bool(record.success)),
            "progress": float(record.score),
            "steps": float(record.steps),
            "knowledge": (grade.get("knowledge") or {}).get("score"),
            "stale": (grade.get("stale") or {}).get("score"),
            "detected": found,
        }
        for name in ("alternatives", "controls", "premature_commit"):
            value = found.get(name)
            row[name] = None if value is None else float(bool(value))
        for name in ("confounds", "revision"):
            value = found.get(name)
            row[name] = None if value is None else float(value)
        row["repeated_measurements"] = float(found.get("repeated_measurements", 0) > 0)
        row["first_test_old_answer"] = None
        world = episode["world"]
        if world["scenario"] == "Combinatorial Chemistry" and found.get("first_test"):
            current = _chemistry_answer(world)
            olds = {
                _chemistry_answer(w)
                for w in experience_worlds
                if w["scenario"] == world["scenario"]
                and w["difficulty"] == world["difficulty"]
                and w["seed"] != world["seed"]
            } - {current}
            if olds:
                row["first_test_old_answer"] = float(frozenset(found["first_test"]) in olds)
        row["cited_strategy"] = None
        if traj is not None and episode["phase"] != "experience":
            texts = strategies.setdefault(episode["run"], _strategy_texts(episode["run"]))
            cited = _cited(traj, texts)
            row["cited_strategy"] = None if cited is None else float(cited)
        codes = ((grade.get("behaviour_codes") or {}).get("codes")) or {}
        for name in CODED:
            present = (codes.get(name) or {}).get("present")
            row[f"coded_{name}"] = None if present is None else float(present)
        rows.append(row)
    return rows


def _cell(rows: Iterable[dict[str, Any]], metric: str) -> str:
    values = [r[metric] for r in rows if r.get(metric) is not None]
    if not values:
        return "n/a"
    mean, low, high = mean_interval(values)
    return f"{mean:.2f} [{low:.2f}, {high:.2f}] (n={len(values)})"


def _by_world(rows: list[dict[str, Any]], metric: str) -> dict[tuple[Any, ...], float]:
    """Each world's value averaged over repeats, keyed by its place in the design."""
    groups: dict[tuple[Any, ...], list[float]] = defaultdict(list)
    for r in rows:
        if r.get(metric) is not None:
            key = (r["phase"], r["condition"], r["position"])
            groups[key].append(r[metric])
    return {k: sum(v) / len(v) for k, v in groups.items()}


def paired(
    rows: list[dict[str, Any]], arm_a: str, arm_b: str, metric: str, phase: str, condition: str
) -> dict[str, Any] | None:
    a = _by_world(
        [
            r
            for r in rows
            if r["arm"] == arm_a and r["phase"] == phase and r["condition"] == condition
        ],
        metric,
    )
    b = _by_world(
        [
            r
            for r in rows
            if r["arm"] == arm_b and r["phase"] == phase and r["condition"] == condition
        ],
        metric,
    )
    shared = sorted(set(a) & set(b))
    if len(shared) < 2:
        return None
    return paired_compare([a[k] for k in shared], [b[k] for k in shared]).to_dict()


def _fmt(d: dict[str, Any] | None) -> str:
    if d is None:
        return "n/a"
    return f"{d['diff']:+.2f} [{d['ci_low']:+.2f}, {d['ci_high']:+.2f}] (n={d['n']})"


def build_report(out: str | Path) -> dict[str, Any]:
    out = Path(out)
    protocol = json.loads((out / "protocol.json").read_text())
    rows = collect(out)
    arms = list(protocol["arms"])
    conditions = list(protocol["transfer"])
    phases = ["experience"] + [
        p for p in dict.fromkeys(r["phase"] for r in rows) if p and p != "experience"
    ]
    summary: dict[str, Any] = {
        "protocol": protocol["name"],
        "stand_in": any(r["stand_in"] for r in rows),
        "graded": any(r["knowledge"] is not None for r in rows),
        "episodes": len(rows),
        "cells": {},
        "paired": {},
        "lesions": {},
        "learning": {},
    }
    for arm in arms:
        for phase in phases:
            for condition in ["experience"] if phase == "experience" else conditions:
                cell = [
                    r
                    for r in rows
                    if r["arm"] == arm and r["phase"] == phase and r["condition"] == condition
                ]
                if not cell:
                    continue
                summary["cells"][f"{arm}|{phase}|{condition}"] = {
                    m: _cell(cell, m)
                    for m in (*OUTCOMES, *BEHAVIOURS, *(f"coded_{c}" for c in CODED))
                }
    baselines = [b for b in ("hypothesizer", "reasoningbank") if b in arms]
    for baseline in baselines:
        for arm in arms:
            if arm == baseline:
                continue
            for condition in conditions:
                summary["paired"][f"{arm} minus {baseline}|{condition}"] = {
                    m: paired(rows, arm, baseline, m, "transfer", condition)
                    for m in (*OUTCOMES, *BEHAVIOURS)
                }
    for arm, lesions in (protocol.get("lesions") or {}).items():
        for lesion in lesions:
            phase = f"lesion-{lesion['name']}"
            for condition in conditions:
                a = [
                    r
                    for r in rows
                    if r["arm"] == arm and r["phase"] == "transfer" and r["condition"] == condition
                ]
                b = [
                    r
                    for r in rows
                    if r["arm"] == arm and r["phase"] == phase and r["condition"] == condition
                ]
                result = {}
                for m in (*OUTCOMES, *BEHAVIOURS):
                    xa, xb = _by_world(a, m), _by_world(b, m)
                    xa = {k[2]: v for k, v in xa.items()}
                    xb = {k[2]: v for k, v in xb.items()}
                    shared = sorted(set(xa) & set(xb))
                    result[m] = (
                        paired_compare([xa[k] for k in shared], [xb[k] for k in shared]).to_dict()
                        if len(shared) >= 2
                        else None
                    )
                summary["lesions"][f"{arm} minus {arm} with {lesion['name']}|{condition}"] = result
    for arm in arms:
        cell = sorted(
            (r for r in rows if r["arm"] == arm and r["phase"] == "experience"),
            key=lambda r: r["position"],
        )
        if len(cell) < 2:
            continue
        half = max(r["position"] for r in cell) / 2
        first = [r for r in cell if r["position"] < half]
        second = [r for r in cell if r["position"] >= half]
        summary["learning"][arm] = {
            m: {"first_half": _cell(first, m), "second_half": _cell(second, m)}
            for m in (
                "completion",
                "progress",
                "knowledge",
                "alternatives",
                "confounds",
                "revision",
            )
        }
    (out / "report.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=1, default=str)
    )
    (out / "report.md").write_text(render(summary, protocol))
    return summary


def render(summary: dict[str, Any], protocol: dict[str, Any]) -> str:
    lines = [f"# {protocol.get('title', protocol['name'])}", ""]
    if summary["stand_in"]:
        lines += [
            "> **These numbers are not results.** The runs used `offline-demo`, a rule-based "
            "stand-in for a language model. This report shows that the protocol runs end to end "
            "and what its output looks like.",
            "",
        ]
    if not summary["graded"]:
        lines += [
            "Knowledge and stale-knowledge scores are missing: run `sea discovery grade` first.",
            "",
        ]
    lines += [
        f"Model: `{protocol['model'].get('llm')}`. Episodes: {summary['episodes']}. Values are "
        "means with 95% bootstrap intervals over episodes; paired differences are over worlds, "
        "repeats averaged first. Definitions: `docs/metrics.md`, section 10.",
        "",
    ]
    for title, columns in (
        ("Outcomes by arm and condition", OUTCOMES),
        ("Behaviours detected from the actions", BEHAVIOURS),
    ):
        lines += [f"## {title}", ""]
        lines.append("| arm | phase | condition | " + " | ".join(columns) + " |")
        lines.append("|---|---|---|" + "---|" * len(columns))
        for key, cell in summary["cells"].items():
            arm, phase, condition = key.split("|")
            lines.append(
                f"| {arm} | {phase} | {condition} | " + " | ".join(cell[m] for m in columns) + " |"
            )
        lines.append("")
    metrics = (*OUTCOMES, *BEHAVIOURS)
    coded = [f"coded_{c}" for c in CODED]
    lines += [
        "## Behaviours as coded by a model (blind to the arm)",
        "",
        "Not a result until the coder's agreement with people has been measured "
        "(`sea discovery agreement`).",
        "",
        "| arm | phase | condition | " + " | ".join(coded) + " |",
        "|---|---|---|" + "---|" * len(coded),
    ]
    for key, cell in summary["cells"].items():
        arm, phase, condition = key.split("|")
        lines.append(
            f"| {arm} | {phase} | {condition} | " + " | ".join(cell[m] for m in coded) + " |"
        )
    for title, block in (
        ("Paired differences on the transfer worlds", summary["paired"]),
        ("Lesions: the same frozen memory with one kind removed", summary["lesions"]),
    ):
        if not block:
            continue
        lines += [
            "",
            f"## {title}",
            "",
            "Mean paired difference, 95% bootstrap interval, number of worlds; n/a where fewer "
            "than two worlds can be paired.",
            "",
            "| comparison | condition | " + " | ".join(metrics) + " |",
        ]
        lines.append("|---|---|" + "---|" * len(metrics))
        for key, values in block.items():
            name, condition = key.split("|")
            lines.append(
                f"| {name} | {condition} | " + " | ".join(_fmt(values[m]) for m in metrics) + " |"
            )
    if summary["learning"]:
        lines += [
            "",
            "## Over the experience phase: first half against second half",
            "",
            "| arm | metric | first half | second half |",
            "|---|---|---|---|",
        ]
        for arm, values in summary["learning"].items():
            for metric, halves in values.items():
                lines.append(
                    f"| {arm} | {metric} | {halves['first_half']} | {halves['second_half']} |"
                )
    lines.append("")
    return "\n".join(lines)
