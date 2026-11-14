"""Comparing stream methods fairly: one protocol, the same tasks, model and budget for every arm.

A protocol is a JSON file that fixes everything the arms share (the task stream and
its order, the agent, the model, the embedder, the budget per arm, the number of
repeats) and lists the arms, each a method with its options. ``sea compare run``
executes every arm on the same stream; ``sea compare report`` tabulates every metric
per arm and the paired differences against the baseline arm, task by task.

The arms never see each other: each has its own run directory, memory and model-call
cache. What they share is fixed by the protocol and written into each run's
``config.json``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .experiments import paired_compare
from .methods.registry import METHODS, make_config
from .methods.run import run_method
from .methods.stream import TaskRecord, load_records, summarise
from .tasks import parse_seeds, task_stream
from .types import Task


def load_protocol(path: str | Path) -> dict[str, Any]:
    """Read a protocol and check it before anything is spent on it."""
    protocol = json.loads(Path(path).read_text())
    for key in ("name", "stream", "arms", "baseline"):
        if key not in protocol:
            raise ValueError(f"protocol has no '{key}'")
    arms = protocol["arms"]
    if protocol["baseline"] not in arms:
        raise ValueError(f"baseline arm {protocol['baseline']!r} is not one of the arms")
    for name, arm in arms.items():
        method = arm.get("method")
        if method not in METHODS or METHODS[method].runner != "stream":
            raise ValueError(f"arm {name!r}: {method!r} is not a stream method")
        make_config(method, arm.get("options"))  # raises on an unknown option
    return protocol


def protocol_tasks(protocol: dict[str, Any]) -> list[Task]:
    stream = dict(protocol["stream"])
    env = stream.pop("env")
    seeds = parse_seeds(stream.pop("seeds"))
    return task_stream(env, seeds, **stream)


def run_protocol(
    protocol: dict[str, Any],
    out: str | Path,
    *,
    llm: str | None = None,
    arms: list[str] | None = None,
    repeats: int | None = None,
    quiet: bool = False,
    llm_options: dict[str, Any] | None = None,
    embedder: str | None = None,
    embedder_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run every arm of the protocol on the same task stream.

    ``llm`` overrides the protocol's model for every arm (``offline-demo`` gives a
    dry run of the whole protocol), and ``llm_options`` its backend options; the same
    for the embedder. Runs go to ``out/<arm>/rep-<i>/`` and continue from their caches
    when repeated.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    model = dict(protocol.get("model") or {})
    if llm:
        model["llm"] = llm
        # Options belong to a backend: those of the protocol's model do not carry over.
        model["llm_options"] = dict(llm_options or {})
    elif llm_options:
        model["llm_options"] = {**(model.get("llm_options") or {}), **llm_options}
    if embedder:
        model["embedder"] = embedder
        model["embedder_options"] = dict(embedder_options or {})
    elif embedder_options:
        model["embedder_options"] = {**(model.get("embedder_options") or {}), **embedder_options}
    budget = protocol.get("budget") or {}
    n_repeats = int(repeats or protocol.get("repeats", 1))
    tasks = protocol_tasks(protocol)
    resolved = {**protocol, "model": model, "repeats": n_repeats, "tasks": len(tasks)}
    (out / "protocol.json").write_text(json.dumps(resolved, indent=2))
    statuses: dict[str, list[int]] = {}
    for name, arm in protocol["arms"].items():
        if arms and name not in arms:
            continue
        statuses[name] = []
        for rep in range(n_repeats):
            if not quiet:
                print(f"=== arm {name} (method {arm['method']}), repeat {rep + 1} of {n_repeats}")
            status, _ = run_method(
                arm["method"],
                tasks,
                out / name / f"rep-{rep}",
                llm=model.get("llm", "anthropic:claude-opus-5-5"),
                options=arm.get("options"),
                agent=arm.get("agent", protocol.get("agent", "stepwise")),
                agent_options=protocol.get("agent_options"),
                embedder=model.get("embedder", "hashing"),
                effort=model.get("effort"),
                llm_options=model.get("llm_options"),
                embedder_options=model.get("embedder_options"),
                max_cost=budget.get("max_cost_usd_per_run"),
                max_calls=budget.get("max_calls_per_run"),
                quiet=quiet,
                extra_config={"protocol": protocol["name"], "arm": name, "repeat": rep},
            )
            statuses[name].append(status)
    return statuses


# --------------------------------------------------------------------------- reporting


def _arm_runs(out: Path, name: str) -> list[Path]:
    return sorted(p for p in (out / name).glob("rep-*") if (p / "records.jsonl").exists())


def _per_task(runs: list[list[TaskRecord]]) -> dict[str, dict[str, float]]:
    """Each task's metrics averaged over the repeats that completed it, keyed by position."""
    out: dict[str, dict[str, float]] = {}
    longest = max(len(r) for r in runs)
    for position in range(longest):
        rows = [r[position] for r in runs if len(r) > position]
        key = f"{position:04d}:{rows[0].task['name']}:{rows[0].task['seed']}"
        known = [r for r in rows if r.success is not None]
        out[key] = {
            "score": sum(r.score for r in rows) / len(rows),
            "success": sum(float(r.success) for r in known) / len(known) if known else float("nan"),
            "lost": sum(float(r.failure is not None) for r in rows) / len(rows),
            "steps": sum(float(r.steps) for r in rows) / len(rows),
            "group": rows[0].task["name"],
        }
    return out


def _paired(
    tasks: dict[str, dict[str, Any]], base: dict[str, dict[str, Any]], keys: list[str]
) -> dict[str, Any]:
    """Paired differences (arm minus baseline) over the given tasks, one entry per metric."""
    row: dict[str, Any] = {"tasks": len(keys)}
    if len(keys) < 2:
        return row
    for metric in ("score", "success", "lost", "steps"):
        a = [tasks[k][metric] for k in keys]
        b = [base[k][metric] for k in keys]
        if any(x != x or y != y for x, y in zip(a, b, strict=True)):
            continue  # a metric the environment does not define
        row[metric] = paired_compare(a, b).to_dict()
    return row


def report_protocol(out: str | Path) -> dict[str, Any]:
    """Tabulate a protocol's runs: every metric per arm, and paired differences to the baseline."""
    out = Path(out)
    protocol = json.loads((out / "protocol.json").read_text())
    baseline = protocol["baseline"]
    arms: dict[str, Any] = {}
    per_task: dict[str, dict[str, dict[str, float]]] = {}
    for name, arm in protocol["arms"].items():
        run_dirs = _arm_runs(out, name)
        if not run_dirs:
            continue
        runs = [load_records(p / "records.jsonl") for p in run_dirs]
        summaries = [json.loads((p / "summary.json").read_text()) for p in run_dirs]
        per_task[name] = _per_task(runs)
        pooled = [record for run in runs for record in run]
        half = max(len(runs[0]) // 2, 1)
        first = [r.score for run in runs for r in run[:half]]
        second = [r.score for run in runs for r in run[half:]]
        llm = [s["llm"] for s in summaries]
        arms[name] = {
            "method": arm["method"],
            "options": arm.get("options") or {},
            "origin": METHODS[arm["method"]].origin,
            "repeats": len(runs),
            "tasks_completed": [len(r) for r in runs],
            "metrics": summarise(pooled),
            "per_repeat_mean_score": [summarise(r)["mean_score"] for r in runs],
            "first_half_mean_score": round(sum(first) / len(first), 4) if first else None,
            "second_half_mean_score": round(sum(second) / len(second), 4) if second else None,
            "by_group": {
                group: summarise([r for r in pooled if r.task["name"] == group])
                for group in dict.fromkeys(r.task["name"] for r in pooled)
            },
            "cost": {
                "model_calls_per_run": round(sum(c.get("calls", 0) for c in llm) / len(llm), 1),
                "input_tokens_per_run": round(
                    sum(c.get("usage", {}).get("input_tokens", 0) for c in llm) / len(llm)
                ),
                "output_tokens_per_run": round(
                    sum(c.get("usage", {}).get("output_tokens", 0) for c in llm) / len(llm)
                ),
                "estimated_usd_per_run": (
                    None
                    if any(c.get("estimated_cost_usd") is None for c in llm)
                    else round(sum(c["estimated_cost_usd"] for c in llm) / len(llm), 4)
                ),
            },
            "stand_in_model": any(s.get("stand_in_model") for s in summaries),
        }
    comparisons: dict[str, Any] = {}
    if baseline in per_task:
        base = per_task[baseline]
        for name, tasks in per_task.items():
            if name == baseline:
                continue
            shared = [k for k in tasks if k in base]
            row = _paired(tasks, base, shared)
            groups = list(dict.fromkeys(tasks[k]["group"] for k in shared))
            if len(groups) > 1:
                row["by_group"] = {
                    g: _paired(tasks, base, [k for k in shared if tasks[k]["group"] == g])
                    for g in groups
                }
            comparisons[f"{name}_minus_{baseline}"] = row
    result = {
        "protocol": protocol["name"],
        "title": protocol.get("title", protocol["name"]),
        "baseline": baseline,
        "model": protocol.get("model"),
        "stream": protocol["stream"],
        "stand_in_model": any(a["stand_in_model"] for a in arms.values()),
        "arms": arms,
        "comparisons": comparisons,
    }
    (out / "comparison.json").write_text(json.dumps(result, indent=1))
    (out / "comparison.md").write_text(render_comparison(result))
    return result


def _fmt(value: Any, pattern: str = "{:+.3f}") -> str:
    return "n/a" if value is None else pattern.format(value)


def render_comparison(result: dict[str, Any]) -> str:
    lines = [f"# {result['title']}", ""]
    if result["stand_in_model"]:
        lines += [
            "> **These numbers are not results.** The runs used `offline-demo`, a rule-based "
            "stand-in for a language model. This report shows that the protocol runs end to "
            "end and what its output looks like.",
            "",
        ]
    model = result.get("model") or {}
    stream = result["stream"]
    lines += [
        f"Model: `{model.get('llm', '?')}`"
        + (f" with `{json.dumps(model['llm_options'])}`" if model.get("llm_options") else "")
        + f"; embedder: `{model.get('embedder', 'hashing')}`"
        + (
            f" with `{json.dumps(model['embedder_options'])}`"
            if model.get("embedder_options")
            else ""
        )
        + f". Stream: `{json.dumps(stream)}`. Every arm ran the same tasks in the same order.",
        "",
        "## Arms",
        "",
        "| arm | method | origin | options changed | repeats | tasks |",
        "|---|---|---|---|---|---|",
    ]
    for name, arm in result["arms"].items():
        options = ", ".join(f"{k}={v}" for k, v in arm["options"].items()) or "none"
        lines.append(
            f"| {name} | `{arm['method']}` | {arm['origin']} | {options} | {arm['repeats']} | "
            f"{', '.join(str(n) for n in arm['tasks_completed'])} |"
        )
    lines += [
        "",
        "## Outcome metrics",
        "",
        "| arm | mean score | success rate | lost | mean steps | first half | second half | "
        "judge agreement |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, arm in result["arms"].items():
        m = arm["metrics"]
        lines.append(
            f"| {name} | {_fmt(m.get('mean_score'))} | {_fmt(m.get('success_rate'), '{:.1%}')} | "
            f"{_fmt(m.get('failure_rate'), '{:.1%}')} | {_fmt(m.get('mean_steps'), '{:.1f}')} | "
            f"{_fmt(arm['first_half_mean_score'])} | {_fmt(arm['second_half_mean_score'])} | "
            f"{_fmt(m.get('judge_agreement'), '{:.1%}')} |"
        )
    lines += [
        "",
        "First and second half are the mean score over the first and the second half of the "
        "stream: a memory that learns should gain in the second half; the no-memory arm "
        "should not.",
        "",
        f"## Paired differences against `{result['baseline']}`",
        "",
        "Per task, on the same task and seed (repeats averaged first). Mean difference, 95% "
        "bootstrap interval, permutation p-value.",
        "",
        "| comparison | tasks | score | success rate | lost | steps |",
        "|---|---|---|---|---|---|",
    ]
    for name, row in result["comparisons"].items():
        cells = []
        for metric in ("score", "success", "lost", "steps"):
            d = row.get(metric)
            cells.append(
                "n/a"
                if d is None
                else f"{d['diff']:+.3f} [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}], p = {d['p_value']:.3f}"
            )
        lines.append(
            f"| {name.replace('_minus_', ' minus ')} | {row['tasks']} | " + " | ".join(cells) + " |"
        )
    lines += [
        "",
        "## Cost per run",
        "",
        "| arm | model calls | input tokens | output tokens | estimated USD |",
        "|---|---|---|---|---|",
    ]
    for name, arm in result["arms"].items():
        c = arm["cost"]
        usd = "n/a" if c["estimated_usd_per_run"] is None else f"{c['estimated_usd_per_run']:.2f}"
        lines.append(
            f"| {name} | {c['model_calls_per_run']:g} | {c['input_tokens_per_run']:,} | "
            f"{c['output_tokens_per_run']:,} | {usd} |"
        )
    groups = list(dict.fromkeys(g for a in result["arms"].values() for g in a["by_group"]))
    if len(groups) > 1:
        lines += ["", "## By task group", "", "| arm | " + " | ".join(groups) + " |"]
        lines.append("|---|" + "---|" * len(groups))
        for name, arm in result["arms"].items():
            cells = [
                f"{_fmt(arm['by_group'].get(g, {}).get('mean_score'))} "
                f"({_fmt(arm['by_group'].get(g, {}).get('failure_rate'), '{:.0%}')} lost)"
                for g in groups
            ]
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines += [
            "",
            f"Paired difference in score against `{result['baseline']}` within each group:",
            "",
            "| comparison | " + " | ".join(groups) + " |",
            "|---|" + "---|" * len(groups),
        ]
        for name, row in result["comparisons"].items():
            cells = []
            for g in groups:
                d = (row.get("by_group") or {}).get(g, {}).get("score")
                cells.append(
                    "n/a"
                    if d is None
                    else f"{d['diff']:+.3f} [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}]"
                )
            lines.append(f"| {name.replace('_minus_', ' minus ')} | " + " | ".join(cells) + " |")
    variable = [n for n, a in result["arms"].items() if a["repeats"] > 1]
    if variable:
        lines += ["", "## Mean score of each repeat", ""]
        for name in variable:
            scores = result["arms"][name]["per_repeat_mean_score"]
            lines.append(f"- {name}: " + ", ".join(_fmt(s) for s in scores))
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- commands


def cmd_compare_run(args: argparse.Namespace) -> int:
    try:
        protocol = load_protocol(args.protocol)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    from .llm import parse_options

    try:
        llm_options = parse_options(args.llm_option)
        embedder_options = parse_options(args.embedder_option)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    statuses = run_protocol(
        protocol,
        args.out,
        llm=args.llm,
        arms=args.arms.split(",") if args.arms else None,
        repeats=args.repeats,
        llm_options=llm_options,
        embedder=args.embedder,
        embedder_options=embedder_options,
    )
    result = report_protocol(args.out)
    print(render_comparison(result))
    print(f"Report: {Path(args.out) / 'comparison.md'}")
    return 2 if any(s for runs in statuses.values() for s in runs) else 0


def cmd_compare_report(args: argparse.Namespace) -> int:
    result = report_protocol(args.out)
    print(render_comparison(result))
    return 0


def add_compare_commands(sub: Any) -> None:
    compare = sub.add_parser(
        "compare", help="run several methods on the same task stream"
    ).add_subparsers(dest="compare_command", required=True)
    run = compare.add_parser("run", help="run every arm of a protocol and report")
    run.add_argument("--protocol", required=True, help="JSON protocol file (see protocols/)")
    run.add_argument("--out", required=True, help="directory for the arms' runs")
    run.add_argument(
        "--llm",
        help="model for every arm (overrides the protocol): anthropic:<model>, "
        "openai:<model>[@<address>], ollama:<model>[@<address>], hf:<model> or offline-demo",
    )
    run.add_argument(
        "--llm-option",
        action="append",
        metavar="NAME=VALUE",
        help="an option of the model backend (added to, or replacing, the protocol's)",
    )
    run.add_argument("--embedder", help="embedder for every arm (overrides the protocol)")
    run.add_argument(
        "--embedder-option", action="append", metavar="NAME=VALUE", help="an option of the embedder"
    )
    run.add_argument("--arms", help="comma-separated subset of the arms to run")
    run.add_argument("--repeats", type=int, help="repeats per arm (overrides the protocol)")
    run.set_defaults(func=cmd_compare_run)
    report = compare.add_parser("report", help="tabulate the runs of a protocol again")
    report.add_argument("out")
    report.set_defaults(func=cmd_compare_report)
