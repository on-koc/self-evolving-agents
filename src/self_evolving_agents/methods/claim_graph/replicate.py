"""Replicating a claim study from different training seeds.

One run of a study yields one graph. The intervals reported for its held-out score
say how sure we are of *that graph's* score. They say nothing about how different the
graph would have been had the experiments drawn other seeds: which comparisons came
out decisive, where the boundaries fell, which settings ended up recommended.

Replication measures that. The same study is run again with different training seeds,
and every replicate is evaluated on the same held-out conditions and the same held-out
seeds, so that the spread between replicates is the run-to-run variability of the
whole procedure.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .graph import ClaimGraph
from .schema import Claim


def check_seeds(config: dict[str, Any]) -> None:
    """Refuse a configuration whose training seeds overlap its held-out or tuning seeds."""
    tester = config.get("tester", {})
    base = int(tester.get("seed_base", 1000))
    training = set(range(base, base + int(tester.get("max_seeds", 48))))
    evaluation = config.get("evaluation") or {}
    for name in ("seeds", "tuning_seeds"):
        pair = evaluation.get(name)
        if pair and training & set(range(int(pair[0]), int(pair[1]))):
            raise ValueError(
                f"training seeds {base}..{max(training)} overlap the evaluation {name} "
                f"{pair[0]}..{pair[1] - 1}"
            )


def run_replicates(
    config: dict[str, Any],
    out: Path,
    seed_bases: Sequence[int],
    *,
    workers: int = 0,
    quiet: bool = False,
) -> dict[str, Path]:
    """Run the study once per training-seed base into ``out/seed-<base>/``.

    All replicates share one episode cache (``out/episodes.sqlite``): the held-out
    episodes of the reference policy and of the grid search are the same for every
    replicate and are simulated once. Running again continues from the cache.
    """
    from .cli import run_study

    out.mkdir(parents=True, exist_ok=True)
    runs: dict[str, Path] = {}
    for base in seed_bases:
        replicate = json.loads(json.dumps(config))
        replicate.setdefault("tester", {})["seed_base"] = int(base)
        check_seeds(replicate)
        target = out / f"seed-{int(base)}"
        if not quiet:
            print(f"=== replicate with training seeds from {int(base)} -> {target}", flush=True)
        run_study(
            replicate, target, workers=workers, quiet=quiet, cache_path=out / "episodes.sqlite"
        )
        runs[str(int(base))] = target
    return runs


def _comparison(claim: Claim) -> str:
    return ", ".join(
        f"{p} {claim.intervention[p]:g} vs {claim.baseline[p]:g}" for p in claim.parameters
    )


def _where(conditions: dict[str, float]) -> str:
    return ", ".join(f"{k}={v:g}" for k, v in sorted(conditions.items()))


def _spread(values: Sequence[float]) -> dict[str, Any]:
    n = len(values)
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1)) if n > 1 else 0.0
    return {
        "n": n,
        "mean": round(mean, 6),
        "sd": round(sd, 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "values": [round(v, 6) for v in values],
    }


def summarise_replicates(runs: dict[str, Path]) -> dict[str, Any]:
    """Collect the replicates' held-out results and how far they agree with each other.

    Args:
        runs: label (the training-seed base) to finished run directory.
    """
    per_run: dict[str, Any] = {}
    for label, path in runs.items():
        study = json.loads((path / "study.json").read_text())
        transfer = json.loads((path / "transfer.json").read_text())
        graph = ClaimGraph(path / "graph.json")
        verdicts = {
            _comparison(root): {
                _where(e.conditions): e.label for e in root.evidence if e.kind == "outcome"
            }
            for root in graph.roots()
        }
        groups = {}
        for group, result in transfer.items():
            groups[group] = {
                "methods": {
                    m: {"mean_score": v["mean_score"], "failure_rate": v["failure_rate"]}
                    for m, v in result["overall"].items()
                },
                "comparisons": {name: c["score"] for name, c in result["comparisons"].items()},
                "settings": [
                    {
                        "conditions": row["conditions"],
                        "settings": row["methods"]["conditional"]["settings"],
                        "mean_score": row["methods"]["conditional"]["mean_score"],
                    }
                    for row in result["per_point"]
                ],
            }
        per_run[label] = {
            "experiments": study["experiments"],
            "episodes_used": study["episodes_used"],
            "claims": study["graph"]["claims"],
            "by_status": study["graph"]["by_status"],
            "comparisons": sorted(verdicts),
            "verdicts": verdicts,
            "groups": groups,
        }

    labels = list(per_run)
    first = per_run[labels[0]]
    aggregate: dict[str, Any] = {}
    for group, content in first["groups"].items():
        methods = {
            m: {
                "mean_score": _spread(
                    [per_run[r]["groups"][group]["methods"][m]["mean_score"] for r in labels]
                ),
                "failure_rate": _spread(
                    [per_run[r]["groups"][group]["methods"][m]["failure_rate"] for r in labels]
                ),
            }
            for m in content["methods"]
        }
        comparisons = {}
        for name in content["comparisons"]:
            rows = [per_run[r]["groups"][group]["comparisons"][name] for r in labels]
            comparisons[name] = {
                **_spread([row["diff"] for row in rows]),
                "intervals_above_zero": sum(row["ci_low"] > 0 for row in rows),
                "intervals_below_zero": sum(row["ci_high"] < 0 for row in rows),
            }
        settings = []
        for i, row in enumerate(content["settings"]):
            chosen = Counter(
                json.dumps(per_run[r]["groups"][group]["settings"][i]["settings"], sort_keys=True)
                for r in labels
            )
            settings.append(
                {
                    "conditions": row["conditions"],
                    "choices": [
                        {"settings": json.loads(k), "replicates": n}
                        for k, n in chosen.most_common()
                    ],
                    "mean_score": _spread(
                        [per_run[r]["groups"][group]["settings"][i]["mean_score"] for r in labels]
                    ),
                }
            )
        aggregate[group] = {"methods": methods, "comparisons": comparisons, "settings": settings}

    # Verdicts at the conditions every replicate tested for a comparison every replicate made.
    shared = set(first["comparisons"])
    for label in labels[1:]:
        shared &= set(per_run[label]["comparisons"])
    agreement = []
    for comparison in sorted(shared):
        points = set(first["verdicts"][comparison])
        for label in labels[1:]:
            points &= set(per_run[label]["verdicts"][comparison])
        for point in sorted(points, key=lambda p: [float(x.split("=")[1]) for x in p.split(", ")]):
            counts = Counter(per_run[r]["verdicts"][comparison][point] for r in labels)
            agreement.append(
                {
                    "comparison": comparison,
                    "conditions": point,
                    "verdicts": dict(counts.most_common()),
                    "unanimous": len(counts) == 1,
                }
            )
    return {
        "replicates": labels,
        "per_replicate": per_run,
        "aggregate": aggregate,
        "comparisons_in_every_replicate": sorted(shared),
        "comparisons_in_some_replicates": sorted(
            set().union(*(per_run[r]["comparisons"] for r in labels)) - shared
        ),
        "verdict_agreement": agreement,
    }


_LABELS = {
    "intervention_better": "intervention better",
    "baseline_better": "baseline better",
    "no_benefit": "no meaningful benefit",
    "inconclusive": "unresolved",
}


def render_replication(summary: dict[str, Any], title: str = "Claim study") -> str:
    """Markdown account of a replication summary."""
    labels = summary["replicates"]
    per = summary["per_replicate"]
    lines = [
        f"# Replication across training seeds: {title}",
        "",
        f"{len(labels)} replicates of the same study, with training seeds starting at "
        f"{', '.join(labels)}. Every replicate is evaluated on the same held-out conditions "
        "and the same held-out seeds, so the spread between replicates is the run-to-run "
        "variability of the whole procedure. Methods that do not depend on the experiments "
        "(the reference policy, the grid search) score the same in every replicate.",
        "",
        "## Size and cost of each replicate",
        "",
        "| training seeds from | experiments | episodes | claims | supported | comparisons |",
        "|---|---|---|---|---|---|",
    ]
    for label in labels:
        r = per[label]
        lines.append(
            f"| {label} | {r['experiments']} | {r['episodes_used']} | {r['claims']} | "
            f"{r['by_status'].get('supported', 0)} | {len(r['comparisons'])} |"
        )
    lines.append("")
    if summary["comparisons_in_some_replicates"]:
        lines += [
            "Comparisons proposed in some replicates only: "
            + "; ".join(f"`{c}`" for c in summary["comparisons_in_some_replicates"])
            + ".",
            "",
        ]

    for group, content in summary["aggregate"].items():
        lines += [
            f"## Held-out score: {group}",
            "",
            "| method | mean over replicates | sd | min | max | each replicate |",
            "|---|---|---|---|---|---|",
        ]
        for method, stats in content["methods"].items():
            s = stats["mean_score"]
            each = ", ".join(f"{v:+.3f}" for v in s["values"])
            lines.append(
                f"| {method} | {s['mean']:+.3f} | {s['sd']:.3f} | {s['min']:+.3f} | "
                f"{s['max']:+.3f} | {each} |"
            )
        lines += [
            "",
            "| spacecraft lost | mean over replicates | min | max |",
            "|---|---|---|---|",
        ]
        for method, stats in content["methods"].items():
            s = stats["failure_rate"]
            lines.append(f"| {method} | {s['mean']:.1%} | {s['min']:.1%} | {s['max']:.1%} |")
        lines += [
            "",
            "| paired difference | mean over replicates | sd | min | max | "
            "replicates whose 95% interval excludes zero |",
            "|---|---|---|---|---|---|",
        ]
        for name, s in content["comparisons"].items():
            decided = s["intervals_above_zero"] + s["intervals_below_zero"]
            side = "above" if s["intervals_above_zero"] >= s["intervals_below_zero"] else "below"
            lines.append(
                f"| {name.replace('_', ' ')} | {s['mean']:+.3f} | {s['sd']:.3f} | "
                f"{s['min']:+.3f} | {s['max']:+.3f} | {decided} of {s['n']}"
                + (f" ({side})" if decided else "")
                + " |"
            )
        lines += [
            "",
            "Settings the claim graph recommended at each held-out condition:",
            "",
            "| conditions | settings (number of replicates) | score: mean, min to max |",
            "|---|---|---|",
        ]
        for row in content["settings"]:
            choices = "; ".join(
                (", ".join(f"{k}={v:g}" for k, v in sorted(c["settings"].items())) or "reference")
                + f" ({c['replicates']})"
                for c in row["choices"]
            )
            s = row["mean_score"]
            lines.append(
                f"| {_where(row['conditions'])} | {choices} | {s['mean']:+.3f}, "
                f"{s['min']:+.3f} to {s['max']:+.3f} |"
            )
        lines.append("")

    rows = summary["verdict_agreement"]
    if rows:
        unanimous = sum(r["unanimous"] for r in rows)
        lines += [
            "## Do the replicates reach the same verdicts?",
            "",
            f"Tests made by every replicate at the same conditions: {len(rows)}. "
            f"Unanimous: {unanimous} ({unanimous / len(rows):.0%}).",
            "",
            "| comparison | conditions | verdicts (number of replicates) |",
            "|---|---|---|",
        ]
        for r in rows:
            verdicts = ", ".join(f"{_LABELS.get(k, k)} ({n})" for k, n in r["verdicts"].items())
            mark = "" if r["unanimous"] else " **differ**"
            lines.append(f"| `{r['comparison']}` | {r['conditions']} | {verdicts}{mark} |")
        lines.append("")
    return "\n".join(lines)


def compare_runs(
    run_a: Path, run_b: Path, *, cache_path: Path | None = None, workers: int = 0
) -> dict[str, Any]:
    """Paired comparison of what two finished runs recommend, on the same held-out episodes.

    Both runs must share the evaluation section of their configuration (conditions,
    seeds). For every held-out condition each run's graph is asked for its
    recommendation, both policies are run on the same seeds, and the difference
    A minus B is summarised per group of conditions.
    """
    from ...experiments import EpisodeCache, EpisodeRunner, paired_compare
    from ...policies import scanning_policy
    from .evaluate import _run
    from .policy import recommend
    from .testing import Domain

    config_a = json.loads((run_a / "config.json").read_text())
    config_b = json.loads((run_b / "config.json").read_text())
    if config_a.get("evaluation") != config_b.get("evaluation"):
        raise ValueError("the two runs were not evaluated on the same conditions and seeds")
    evaluation = config_a["evaluation"]
    seeds = range(int(evaluation["seeds"][0]), int(evaluation["seeds"][1]))
    domain_a, domain_b = Domain.from_dict(config_a["domain"]), Domain.from_dict(config_b["domain"])
    graph_a, graph_b = ClaimGraph(run_a / "graph.json"), ClaimGraph(run_b / "graph.json")
    groups = evaluation["test_points"]
    if isinstance(groups, list):
        groups = {"held-out conditions": groups}
    out: dict[str, Any] = {"a": str(run_a), "b": str(run_b), "groups": {}}
    cache = EpisodeCache(cache_path or run_a / "episodes.sqlite")
    with EpisodeRunner(cache, workers=workers) as runner:
        for group, points in groups.items():
            scores_a: list[float] = []
            scores_b: list[float] = []
            lost_a: list[float] = []
            lost_b: list[float] = []
            rows = []
            for point in points:
                conditions = domain_a.conditions(**point)
                rec_a = recommend(graph_a, conditions, domain=domain_a)
                rec_b = recommend(graph_b, domain_b.conditions(**point), domain=domain_b)
                a = _run(runner, domain_a, scanning_policy, conditions, rec_a.settings, seeds)
                b = _run(runner, domain_a, scanning_policy, conditions, rec_b.settings, seeds)
                scores_a += [o.score for o in a]
                scores_b += [o.score for o in b]
                lost_a += [float(o.failure is not None) for o in a]
                lost_b += [float(o.failure is not None) for o in b]
                rows.append(
                    {
                        "conditions": dict(point),
                        "a": {
                            "settings": rec_a.settings,
                            "mean_score": round(sum(o.score for o in a) / len(a), 6),
                        },
                        "b": {
                            "settings": rec_b.settings,
                            "mean_score": round(sum(o.score for o in b) / len(b), 6),
                        },
                        "same_settings": rec_a.settings == rec_b.settings,
                    }
                )
            out["groups"][group] = {
                "a_minus_b": paired_compare(scores_a, scores_b).to_dict(),
                "failure_rate_a": round(sum(lost_a) / len(lost_a), 6),
                "failure_rate_b": round(sum(lost_b) / len(lost_b), 6),
                "per_point": rows,
            }
        out["episodes_simulated"] = runner.episodes_run
    return out
