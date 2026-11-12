"""``sea claims`` commands: run a study, inspect the graph, ask it for a recommendation."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


def _range(pair: list[int]) -> range:
    return range(int(pair[0]), int(pair[1]))


def run_study(
    config: dict[str, Any],
    out: Path,
    *,
    budget: int | None = None,
    workers: int = 0,
    llm_spec: str | None = None,
    evaluate: bool = True,
    quiet: bool = False,
) -> dict[str, Any]:
    """Run a claim study described by ``config`` and write everything to ``out``.

    Re-running into the same directory continues: finished episodes come from the
    cache, and the graph is rebuilt from the same deterministic sequence of
    experiments.
    """
    from ..experiments import EpisodeCache, EpisodeRunner
    from ..policies import scanning_policy
    from ..provenance import ProvenanceStore
    from .evaluate import composition_check, evaluate_transfer
    from .graph import ClaimGraph
    from .hypotheses import LLMProposer, claim_from_spec
    from .loop import ActiveLoop, LadderProposer, Planner
    from .report import render_report
    from .testing import ClaimTester, Domain

    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(config, indent=2))
    domain = Domain.from_dict(config["domain"])
    graph_path = out / "graph.json"
    if graph_path.exists():
        graph_path.unlink()  # the graph is a product of the run; episodes are what is cached
    store = ProvenanceStore(out / "provenance.sqlite")
    store.start_run("claim-study", config.get("name", out.name), config)
    graph = ClaimGraph(graph_path, store=store)
    for spec in config.get("hypotheses", []):
        graph.add(claim_from_spec(spec, env_id=domain.env_id, conditions=list(domain.reference)))

    def show(entry: dict[str, Any]) -> None:
        if not quiet and entry["op"] != "evidence":
            print(
                f"    {entry['op']:10s} {entry['claim'][-6:]}  {entry['detail'][:150]}", flush=True
            )

    started = time.time()
    with EpisodeRunner(EpisodeCache(out / "episodes.sqlite"), workers=workers) as runner:
        tester = ClaimTester(runner, domain, **config.get("tester", {}))
        planner = Planner(graph, domain, sweeps=config.get("sweeps"), **config.get("planner", {}))
        proposers: list[Any] = []
        if config.get("ladders"):
            proposers.append(LadderProposer(config["ladders"], env_id=domain.env_id))
        if llm_spec:
            from ..llm import TrackedLLM, make_backend

            llm = TrackedLLM(make_backend(llm_spec), cache_dir=out / "llm_cache", store=store)
            proposers.append(
                LLMProposer(llm, domain, policy_text=scanning_policy().describe(), every=3)
            )
        loop = ActiveLoop(
            graph,
            tester,
            planner,
            budget_episodes=budget or int(config.get("budget", 2000)),
            per_round=int(config.get("per_round", 3)),
            proposers=proposers,
            on_event=show,
        )
        while tester.episodes < loop.budget:
            done_before = len(loop.experiments)
            if loop.step() == 0:
                break
            if not quiet:
                for x in loop.experiments[done_before:]:
                    print(
                        f"[round {x['round']:2d}] {x['kind']:9s} {x['family'][-6:]} at "
                        f"{x['conditions']} ({x['episodes']} new episodes; "
                        f"{tester.episodes} of {loop.budget} used, {time.time() - started:.0f}s)",
                        flush=True,
                    )
        study = {
            "rounds": loop.rounds,
            "experiments": len(loop.experiments),
            "episodes_run": tester.episodes,
            "budget": loop.budget,
            "wall_s": round(time.time() - started, 1),
            "graph": graph.summary(),
            "confidence_per_look": round(tester.confidence, 4),
        }
        (out / "study.json").write_text(json.dumps(study, indent=2))
        with (out / "experiments.jsonl").open("w") as fh:
            for x in loop.experiments:
                fh.write(json.dumps(x) + "\n")

        transfer = composition = None
        ev = config.get("evaluation")
        if evaluate and ev:
            seeds = _range(ev["seeds"])
            groups = ev["test_points"]
            if isinstance(groups, list):
                groups = {"held-out conditions": groups}
            transfer = {}
            for group, points in groups.items():
                if not quiet:
                    print(f"evaluating transfer: {group} ({len(points)} conditions)", flush=True)
                transfer[group] = evaluate_transfer(
                    runner,
                    graph,
                    domain,
                    points,
                    seeds,
                    oracle_grid=ev.get("oracle_grid"),
                    tuning_seeds=_range(ev["tuning_seeds"]) if ev.get("tuning_seeds") else None,
                )
            (out / "transfer.json").write_text(json.dumps(transfer, indent=2))
            all_points = [p for points in groups.values() for p in points]
            composition = composition_check(
                runner, graph, domain, ev.get("composition_points", all_points), seeds
            )
            (out / "composition.json").write_text(json.dumps(composition, indent=2))
            study["evaluation_wall_s"] = round(time.time() - started - study["wall_s"], 1)
        study["episodes_total"] = len(runner.cache)

    graph.save()
    report = render_report(
        graph,
        title=config.get("title", "Claim study"),
        study=study,
        transfer=transfer,
        composition=composition,
    )
    (out / "report.md").write_text(report)
    (out / "study.json").write_text(json.dumps(study, indent=2))
    store.close()
    return {"study": study, "transfer": transfer, "composition": composition}


def cmd_study(args: argparse.Namespace) -> int:
    config = json.loads(Path(args.config).read_text())
    result = run_study(
        config,
        Path(args.out),
        budget=args.budget,
        workers=args.workers,
        llm_spec=args.llm,
        evaluate=not args.no_eval,
    )
    print(json.dumps(result["study"], indent=2))
    for group, transfer in (result["transfer"] or {}).items():
        print(group, json.dumps(transfer["overall"], indent=2))
    print(f"Report: {Path(args.out) / 'report.md'}")
    return 0


def _load_graph(run: str) -> Any:
    from .graph import ClaimGraph

    path = Path(run) / "graph.json"
    if not path.exists():
        raise SystemExit(f"no graph.json in {run}")
    return ClaimGraph(path)


def cmd_show(args: argparse.Namespace) -> int:
    graph = _load_graph(args.run)
    print(json.dumps(graph.summary(), indent=2))
    for root in graph.roots():
        print(f"\n{root.id}  {root.describe()}")
        for e in sorted(
            (e for e in root.evidence if e.kind == "outcome"),
            key=lambda e: tuple(sorted(e.conditions.items())),
        ):
            print(f"    {e.label:20s} {e.summary()}")
        for mechanism in root.mechanisms:
            print(f"    explanation [{mechanism.status}]: {mechanism.statement}")
            for e in mechanism.evidence:
                print(f"        {e.summary()}")
        for child in graph.children(root.id, active_only=False):
            print(f"  -> {child.id}  {child.describe()}")
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    from ..cli import parse_assignments
    from .policy import assemble_policy
    from .testing import Domain

    graph = _load_graph(args.run)
    config = json.loads((Path(args.run) / "config.json").read_text())
    domain = Domain.from_dict(config["domain"])
    conditions = domain.conditions(**parse_assignments(args.condition))
    for mode in ("reference", "flat", "conditional"):
        policy, rec = assemble_policy(graph, conditions, mode=mode, domain=domain)
        print(f"\n{mode}: {rec.settings or 'reference settings'}")
        for reason in rec.reasons:
            distance = reason["nearest_support_distance"]
            if distance is None:
                footing = "applied without regard to these conditions"
            elif distance == 0:
                footing = "tested exactly here"
            else:
                footing = f"nearest supporting test {distance} log-units away"
            print(f"   because {reason['claim']}: {reason['statement'][:90]} ({footing})")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .report import render_report

    run = Path(args.run)
    graph = _load_graph(args.run)

    def load(name: str) -> Any:
        path = run / name
        return json.loads(path.read_text()) if path.exists() else None

    config = load("config.json") or {}
    text = render_report(
        graph,
        title=config.get("title", "Claim study"),
        study=load("study.json"),
        transfer=load("transfer.json"),
        composition=load("composition.json"),
    )
    target = Path(args.out) if args.out else run / "report.md"
    target.write_text(text)
    print(f"wrote {target}")
    return 0


def add_claims_commands(sub: Any) -> None:
    claims = sub.add_parser("claims", help="claim graph and experiments").add_subparsers(
        dest="claims_command", required=True
    )
    study = claims.add_parser("study", help="run an active-experimentation study")
    study.add_argument("--config", required=True, help="JSON study configuration")
    study.add_argument("--out", required=True, help="run directory")
    study.add_argument(
        "--budget", type=int, help="simulator episodes to spend (overrides the config)"
    )
    study.add_argument("--workers", type=int, default=0, help="parallel simulator processes")
    study.add_argument(
        "--llm", help="also ask this model for hypotheses, e.g. anthropic:claude-opus-5-5"
    )
    study.add_argument(
        "--no-eval", action="store_true", help="skip the held-out transfer evaluation"
    )
    study.set_defaults(func=cmd_study)

    show = claims.add_parser("show", help="print claims, evidence and explanations")
    show.add_argument("run")
    show.set_defaults(func=cmd_show)

    rec = claims.add_parser("recommend", help="settings recommended under given conditions")
    rec.add_argument("run")
    rec.add_argument("--condition", action="append", metavar="NAME=VALUE", required=True)
    rec.set_defaults(func=cmd_recommend)

    report = claims.add_parser("report", help="write the Markdown report")
    report.add_argument("run")
    report.add_argument("--out")
    report.set_defaults(func=cmd_report)
