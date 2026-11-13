"""``sea`` command line.

    sea methods                           the methods, where each comes from, what is known
    sea run --method NAME ...             run one method on a stream of tasks
    sea show RUN                          summary and memory items of a run
    sea compare run|report ...            several methods on the same stream (a protocol)
    sea claims ...                        the claim graph: studies, replication, reports
    sea policy run ...                    run a rule policy (no model) on scanning tasks
    sea prov lineage RUN ID               where a record came from / what it influenced
    sea prov export RUN OUT.json          dump a run's provenance as W3C PROV-JSON
    sea envs                              list environments and scanning regimes

A run lives in one directory: ``config.json``, ``provenance.sqlite``, ``bank.jsonl``,
``records.jsonl``, ``summary.json`` and ``llm_cache/``. Re-running the same command
into the same directory replays cached model calls instead of paying for them again.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .envs import REGIMES, available_envs
from .tasks import ORDERS, parse_seeds, task_stream
from .types import Task


def parse_assignments(pairs: list[str] | None) -> dict[str, float]:
    """``["a=1", "b=0.5"]`` -> ``{"a": 1.0, "b": 0.5}``."""
    out: dict[str, float] = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep:
            raise argparse.ArgumentTypeError(f"expected name=value, got {pair!r}")
        out[key.strip()] = float(value)
    return out


def parse_options(pairs: list[str] | None) -> dict[str, Any]:
    """``["retrieve_k=2", "judge=env", "memory=false"]`` -> typed values.

    A value that reads as JSON (a number, ``true``, ``null``) is taken as such;
    anything else is a string.
    """
    out: dict[str, Any] = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"expected name=value, got {pair!r}")
        try:
            out[key.strip()] = json.loads(value)
        except json.JSONDecodeError:
            out[key.strip()] = value
    return out


def build_tasks(args: argparse.Namespace) -> list[Task]:
    """Expand the task options into an ordered stream."""
    if args.env == "discoveryworld" and not args.scenario:
        raise SystemExit("--scenario is required for discoveryworld")
    params: dict[str, Any] = dict(parse_assignments(args.param))
    if args.duration:
        params["duration_s"] = args.duration
    return task_stream(
        args.env,
        parse_seeds(args.seeds),
        regimes=[r.strip() for r in args.regime.split(",") if r.strip()],
        order=args.order,
        conditions=parse_assignments(args.condition) or None,
        params=params,
        scenarios=[s.strip() for s in (args.scenario or "").split(";") if s.strip()],
        difficulty=args.difficulty,
        max_steps=args.max_steps,
    )


def _add_task_options(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("tasks")
    g.add_argument("--env", default="bsk-scan", choices=available_envs())
    g.add_argument("--seeds", default="0:10", help='e.g. "0:10" or "1,4,9" (default 0:10)')
    g.add_argument(
        "--regime",
        default="nominal",
        help=f"scanning regime(s), comma separated: {', '.join(REGIMES)}",
    )
    g.add_argument(
        "--condition",
        action="append",
        metavar="NAME=VALUE",
        help="override an operating condition (scanning)",
    )
    g.add_argument(
        "--param",
        action="append",
        metavar="NAME=VALUE",
        help="override an episode parameter (scanning)",
    )
    g.add_argument("--duration", type=float, help="episode length in seconds (scanning)")
    g.add_argument("--scenario", help='DiscoveryWorld scenario name(s), separated by ";"')
    g.add_argument(
        "--difficulty", default="Normal", help="DiscoveryWorld difficulty (Easy, Normal, Challenge)"
    )
    g.add_argument("--max-steps", type=int, default=100, help="DiscoveryWorld step limit")
    g.add_argument(
        "--order",
        default="sequential",
        choices=list(ORDERS),
        help="with several regimes or scenarios: finish one before the next, or alternate",
    )


def _add_model_options(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("model")
    g.add_argument(
        "--llm",
        default="anthropic:claude-opus-5-5",
        help="'anthropic:<model>' or 'offline-demo' (a scripted stand-in, for dry runs)",
    )
    g.add_argument(
        "--effort", choices=["low", "medium", "high", "xhigh", "max"], help="Claude effort level"
    )
    g.add_argument(
        "--embedder",
        default="hashing",
        help="'hashing' (offline, word overlap) or 'gemini' (the paper's embedding model)",
    )
    g.add_argument(
        "--max-cost", type=float, help="stop when the estimated spend reaches this many USD"
    )
    g.add_argument("--max-calls", type=int, help="stop after this many uncached model calls")


# --------------------------------------------------------------------------- commands


def cmd_envs(args: argparse.Namespace) -> int:
    print("Environments:", ", ".join(available_envs()))
    print("\nScanning regimes (single-factor departures from the reference spacecraft):")
    for name, overrides in REGIMES.items():
        print(f"  {name:18s} {overrides or 'reference configuration'}")
    return 0


def cmd_methods(args: argparse.Namespace) -> int:
    from .methods.registry import METHODS, defaults

    for spec in METHODS.values():
        how = "sea run --method " + spec.name if spec.runner == "stream" else "sea claims study"
        print(f"{spec.name}  ({spec.origin})  {spec.title}")
        print(f"    {spec.summary}")
        print(f"    evidence: {spec.evidence}")
        print(f"    run with: {how}    documentation: {spec.doc}")
        if args.options and spec.runner == "stream":
            for key, value in defaults(spec.name).items():
                print(f"      {key} = {value!r}")
        print()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from .methods.run import run_method

    try:
        status, summary = run_method(
            args.method,
            build_tasks(args),
            args.out,
            llm=args.llm,
            options=parse_options(args.set),
            agent=args.agent,
            embedder=args.embedder,
            effort=args.effort,
            max_cost=args.max_cost,
            max_calls=args.max_calls,
            bank=args.bank,
            store_steps=not args.no_steps,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print(json.dumps(summary, indent=2))
    print(f"Run written to {args.out}/")
    return status


def cmd_show(args: argparse.Namespace) -> int:
    from .methods.reasoningbank import ReasoningBank

    run = Path(args.run)
    summary_path = run / "summary.json"
    if summary_path.exists():
        print(summary_path.read_text())
    bank_path = run / "bank.jsonl"
    if not bank_path.exists():
        print("\nThis run has no memory bank.")
        return 0
    bank = ReasoningBank(bank_path)
    print(f"\n{len(bank.items)} memory items in {len(bank)} experiences:")
    for experience in bank.experiences:
        for item in experience.items:
            usage = item.meta.get("usage") or {}
            used = (
                f"used {usage['uses']}x, mean reward {usage['score_sum'] / usage['uses']:+.3f}"
                if usage.get("uses")
                else "no usage statistics"
            )
            print(f"\n[{item.id}] ({item.source}; from {experience.task_key}; {used})")
            print(f"  Title: {item.title}\n  When:  {item.description}\n  What:  {item.content}")
    return 0


def cmd_policy_run(args: argparse.Namespace) -> int:
    from .agents import PolicyAgent
    from .envs import make_env
    from .policies import RulePolicy, scanning_policy

    if args.env == "discoveryworld":
        raise SystemExit("rule policies need named features; discoveryworld has none")
    if args.policy:
        policy = RulePolicy.from_dict(json.loads(Path(args.policy).read_text()))
    else:
        policy = scanning_policy(**parse_assignments(args.set))
    print(policy.describe())
    scores, failures = [], {}
    env = None
    for task in build_tasks(args):
        if env is None or not env.retask(task):
            if env is not None:
                env.close()
            env = make_env(task)
        outcome = PolicyAgent(policy).run(env).outcome
        scores.append(outcome.score)
        if outcome.failure:
            failures[outcome.failure] = failures.get(outcome.failure, 0) + 1
        print(
            f"{task.name} seed={task.seed}: score {outcome.score:+.3f} "
            f"{outcome.failure or 'alive'} min battery {outcome.metrics['min_battery']:.2f}"
        )
    if env is not None:
        env.close()
    print(
        f"\nmean score {sum(scores) / len(scores):+.4f} over {len(scores)} episodes; "
        f"failures: {failures or 'none'}"
    )
    return 0


def cmd_prov_lineage(args: argparse.Namespace) -> int:
    from .provenance import ProvenanceStore

    store = ProvenanceStore(Path(args.run) / "provenance.sqlite")
    node = store.get_node(args.id)
    if node is None:
        print(f"no record with id {args.id}")
        return 1
    direction = "downstream" if args.down else "upstream"
    print(f"{node['kind']} {node['id']}  {node['label'] or ''}")
    print("influenced:" if args.down else "derived from:")
    for row in store.lineage(args.id, direction, max_depth=args.depth):
        print(
            f"{'  ' * row['depth']}{row['via']} -> {row['kind']} {row['id']}  {row['label'] or ''}"
        )
    return 0


def cmd_prov_export(args: argparse.Namespace) -> int:
    from .provenance import ProvenanceStore

    store = ProvenanceStore(Path(args.run) / "provenance.sqlite")
    doc = store.export_prov_json()
    Path(args.out).write_text(json.dumps(doc, indent=1))
    print(
        f"wrote {args.out}: " + ", ".join(f"{len(v)} {k}" for k, v in doc.items() if k != "prefix")
    )
    return 0


# --------------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    from .methods.registry import AGENTS, METHODS

    parser = argparse.ArgumentParser(prog="sea", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("envs", help="list environments and regimes").set_defaults(func=cmd_envs)

    methods = sub.add_parser("methods", help="list the methods and what is known about each")
    methods.add_argument("--options", action="store_true", help="also print every option's default")
    methods.set_defaults(func=cmd_methods)

    stream_methods = [m.name for m in METHODS.values() if m.runner == "stream"]
    run = sub.add_parser(
        "run",
        help="run one method on a stream of tasks",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    g = run.add_argument_group("method")
    g.add_argument("--method", required=True, choices=stream_methods)
    g.add_argument(
        "--set",
        action="append",
        metavar="NAME=VALUE",
        help="override one of the method's options (see `sea methods --options`)",
    )
    g.add_argument(
        "--agent",
        default="stepwise",
        choices=list(AGENTS),
        help="stepwise: one model call per action, as in the paper. policy_program: one call "
        "per episode writes a rule policy that is then executed",
    )
    _add_task_options(run)
    _add_model_options(run)
    g = run.add_argument_group("output")
    g.add_argument("--out", required=True, help="run directory")
    g.add_argument("--bank", help="memory bank file to load and extend (default: <out>/bank.jsonl)")
    g.add_argument("--no-steps", action="store_true", help="do not store per-step records")
    run.set_defaults(func=cmd_run)

    show = sub.add_parser("show", help="print a run's summary and memory items")
    show.add_argument("run")
    show.set_defaults(func=cmd_show)

    policy = sub.add_parser("policy", help="rule policies").add_subparsers(
        dest="policy_command", required=True
    )
    prun = policy.add_parser("run", help="run a rule policy on scanning tasks (no model)")
    _add_task_options(prun)
    prun.add_argument(
        "--policy", help="JSON file with a rule policy (default: the reference scanning policy)"
    )
    prun.add_argument(
        "--set",
        action="append",
        metavar="NAME=VALUE",
        help="set a parameter of the reference policy",
    )
    prun.set_defaults(func=cmd_policy_run)

    prov = sub.add_parser("prov", help="provenance").add_subparsers(
        dest="prov_command", required=True
    )
    lineage = prov.add_parser("lineage", help="trace a record")
    lineage.add_argument("run")
    lineage.add_argument("id")
    lineage.add_argument(
        "--down", action="store_true", help="what the record influenced, instead of its sources"
    )
    lineage.add_argument("--depth", type=int, default=6)
    lineage.set_defaults(func=cmd_prov_lineage)
    export = prov.add_parser("export", help="write W3C PROV-JSON")
    export.add_argument("run")
    export.add_argument("out")
    export.set_defaults(func=cmd_prov_export)

    from .methods.claim_graph.cli import add_claims_commands

    add_claims_commands(sub)

    from .compare import add_compare_commands

    add_compare_commands(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
