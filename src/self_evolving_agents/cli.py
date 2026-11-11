"""``sea`` command line.

    sea envs                              list environments and scanning regimes
    sea rb run ...                        run a task stream with reasoning memory
    sea rb show RUN                       summary and memory items of a run
    sea policy run ...                    run a rule policy (no model) on scanning tasks
    sea prov lineage RUN ID               where a record came from / what it influenced
    sea prov export RUN OUT.json          dump a run's provenance as W3C PROV-JSON
    sea claims ...                        claim graph and experiments (see ``sea claims -h``)

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

from .envs import REGIMES, available_envs, discoveryworld_task, scan_task
from .types import Task


def parse_seeds(text: str) -> list[int]:
    """``"0:5"`` -> 0..4, ``"1,4,9"`` -> those, ``"7"`` -> [7]."""
    seeds: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if ":" in part:
            start, stop = part.split(":", 1)
            seeds.extend(range(int(start or 0), int(stop)))
        elif part:
            seeds.append(int(part))
    if not seeds:
        raise argparse.ArgumentTypeError(f"no seeds in {text!r}")
    return seeds


def parse_assignments(pairs: list[str] | None) -> dict[str, float]:
    """``["a=1", "b=0.5"]`` -> ``{"a": 1.0, "b": 0.5}``."""
    out: dict[str, float] = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep:
            raise argparse.ArgumentTypeError(f"expected name=value, got {pair!r}")
        out[key.strip()] = float(value)
    return out


def build_tasks(args: argparse.Namespace) -> list[Task]:
    """Expand the task options into an ordered stream."""
    seeds = parse_seeds(args.seeds)
    if args.env == "discoveryworld":
        if not args.scenario:
            raise SystemExit("--scenario is required for discoveryworld")
        scenarios = [s.strip() for s in args.scenario.split(";") if s.strip()]
        groups = [
            [
                discoveryworld_task(s, args.difficulty, seed=seed, max_steps=args.max_steps)
                for seed in seeds
            ]
            for s in scenarios
        ]
    else:
        params = parse_assignments(args.param)
        if args.duration:
            params["duration_s"] = args.duration
        conditions = parse_assignments(args.condition) or None
        regimes = [r.strip() for r in args.regime.split(",") if r.strip()]
        groups = [
            [
                scan_task(args.env, regime, seed=seed, conditions=conditions, **params)
                for seed in seeds
            ]
            for regime in regimes
        ]
    if args.order == "interleaved":
        return [group[i] for i in range(len(seeds)) for group in groups]
    return [task for group in groups for task in group]


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
        choices=["sequential", "interleaved"],
        help="with several regimes or scenarios: finish one before the next, or alternate",
    )


# --------------------------------------------------------------------------- commands


def cmd_envs(args: argparse.Namespace) -> int:
    print("Environments:", ", ".join(available_envs()))
    print("\nScanning regimes (single-factor departures from the reference spacecraft):")
    for name, overrides in REGIMES.items():
        print(f"  {name:18s} {overrides or 'reference configuration'}")
    return 0


def cmd_rb_run(args: argparse.Namespace) -> int:
    from .agents import PolicyProgramAgent, StepwiseAgent
    from .llm import Budget, BudgetExceeded, TrackedLLM, make_backend
    from .provenance import ProvenanceStore
    from .reasoningbank import ReasoningBank
    from .reasoningbank.induction import EnvJudge, LLMJudge, MemoryExtractor
    from .reasoningbank.pipeline import PipelineConfig, ReasoningBankPipeline

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks = build_tasks(args)
    config = PipelineConfig(
        memory=args.memory,
        scaling=args.scaling,
        k=args.k,
        include_failures=not args.success_only,
        retrieve_k=args.retrieve_k,
        retrieval_mode=args.retrieval,
        max_items=args.max_items,
        condition_weight=args.condition_weight,
        utility_weight=args.utility_weight,
        store_steps=not args.no_steps,
    )
    run_config = {k: v for k, v in vars(args).items() if k != "func"}
    (out / "config.json").write_text(json.dumps(run_config, indent=2, default=str))

    store = ProvenanceStore(out / "provenance.sqlite")
    store.start_run("reasoningbank", out.name, run_config)
    backend_options: dict[str, Any] = {}
    if args.effort and not args.llm.startswith("offline"):
        backend_options["effort"] = args.effort
    llm = TrackedLLM(
        make_backend(args.llm, **backend_options),
        cache_dir=out / "llm_cache",
        budget=Budget(max_cost_usd=args.max_cost, max_calls=args.max_calls),
        store=store,
    )
    agent = StepwiseAgent(llm) if args.agent == "stepwise" else PolicyProgramAgent(llm)
    judge = LLMJudge(llm) if args.judge == "llm" else EnvJudge()
    bank = ReasoningBank(args.bank or out / "bank.jsonl")

    def progress(record: Any) -> None:
        task = record.task
        print(
            f"[{len(pipeline.records):3d}/{len(tasks)}] {task['name']} seed={task['seed']}: "
            f"score {record.score:+.3f} {'ok ' if record.success else 'FAIL'} "
            f"({record.failure or 'no failure'}), {record.steps} steps, judged "
            f"{'success' if record.judged_success else 'failure'}, "
            f"used {len(record.retrieved_item_ids)} items, learned {len(record.new_item_ids)}",
            flush=True,
        )

    pipeline = ReasoningBankPipeline(
        agent,
        judge,
        bank=bank,
        extractor=MemoryExtractor(llm),
        llm=llm,
        store=store,
        config=config,
        on_record=progress,
    )
    if args.llm.startswith("offline"):
        print(
            "NOTE: offline-demo is a rule-based stand-in, not a language model. "
            "This run exercises the pipeline; its numbers are not results."
        )
    status = 0
    try:
        pipeline.run_stream(tasks)
    except BudgetExceeded as exc:
        print(
            f"Stopped: {exc}. Completed {len(pipeline.records)} of {len(tasks)} tasks; "
            "rerun the same command to continue from the cache with a larger budget."
        )
        status = 2
    finally:
        pipeline.save_records(out / "records.jsonl")
        summary = {"pipeline": pipeline.summary(), "bank": bank.stats(), "llm": llm.summary()}
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
        store.close()
    print(json.dumps(summary, indent=2))
    print(f"Run written to {out}/")
    return status


def cmd_rb_show(args: argparse.Namespace) -> int:
    from .reasoningbank import ReasoningBank

    run = Path(args.run)
    summary_path = run / "summary.json"
    if summary_path.exists():
        print(summary_path.read_text())
    bank = ReasoningBank(run / "bank.jsonl")
    print(f"\n{len(bank.items)} memory items in {len(bank)} experiences:")
    for experience in bank.experiences:
        for item in experience.items:
            used = (
                f"used {item.uses}x, mean reward {item.mean_score:+.3f}" if item.uses else "unused"
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
    parser = argparse.ArgumentParser(prog="sea", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("envs", help="list environments and regimes").set_defaults(func=cmd_envs)

    rb = sub.add_parser("rb", help="ReasoningBank pipeline").add_subparsers(
        dest="rb_command", required=True
    )
    run = rb.add_parser(
        "run", help="run a task stream", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    _add_task_options(run)
    g = run.add_argument_group("model")
    g.add_argument(
        "--llm",
        default="anthropic:claude-opus-5-5",
        help="'anthropic:<model>' or 'offline-demo' (a scripted stand-in, for dry runs)",
    )
    g.add_argument(
        "--effort", choices=["low", "medium", "high", "xhigh", "max"], help="Claude effort level"
    )
    g.add_argument(
        "--max-cost", type=float, help="stop when the estimated spend reaches this many USD"
    )
    g.add_argument("--max-calls", type=int, help="stop after this many uncached model calls")
    g = run.add_argument_group("method")
    g.add_argument(
        "--agent",
        default="stepwise",
        choices=["stepwise", "policy"],
        help="stepwise: one model call per action (as in the paper). "
        "policy: one call per episode writes a rule policy that is then executed",
    )
    g.add_argument("--memory", default="reasoningbank", choices=["reasoningbank", "none"])
    g.add_argument(
        "--judge",
        default="llm",
        choices=["llm", "env"],
        help="llm: LLM-as-a-judge, no ground truth. env: the simulator's own criterion",
    )
    g.add_argument(
        "--success-only",
        action="store_true",
        help="ablation: do not learn from failed trajectories",
    )
    g.add_argument(
        "--scaling",
        default="none",
        choices=["none", "parallel", "sequential", "vanilla"],
        help="test-time scaling (MaTTS parallel / sequential, or vanilla TTS)",
    )
    g.add_argument("--k", type=int, default=1, help="scaling factor")
    g.add_argument(
        "--retrieval",
        default="experience",
        choices=["experience", "item"],
        help="experience: the paper's top-k experiences. item: item-level with diversity",
    )
    g.add_argument(
        "--retrieve-k", type=int, default=1, help="experiences to retrieve (experience mode)"
    )
    g.add_argument("--max-items", type=int, help="cap on retrieved items (default 6 in item mode)")
    g.add_argument(
        "--condition-weight",
        type=float,
        default=0.0,
        help="0..1 weight of operating-condition similarity in retrieval",
    )
    g.add_argument(
        "--utility-weight",
        type=float,
        default=0.0,
        help="item mode: bonus for items whose past uses went well",
    )
    g = run.add_argument_group("output")
    g.add_argument("--out", required=True, help="run directory")
    g.add_argument("--bank", help="memory bank file to load and extend (default: <out>/bank.jsonl)")
    g.add_argument("--no-steps", action="store_true", help="do not store per-step records")
    run.set_defaults(func=cmd_rb_run)
    show = rb.add_parser("show", help="print a run's summary and memory items")
    show.add_argument("run")
    show.set_defaults(func=cmd_rb_show)

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

    try:
        from .claims.cli import add_claims_commands
    except ImportError:  # the claim layer is optional at import time
        pass
    else:
        add_claims_commands(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
