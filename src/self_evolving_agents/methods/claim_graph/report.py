"""Human-readable account of a claim graph."""

from __future__ import annotations

from typing import Any

from .graph import ClaimGraph
from .schema import (
    A_BETTER,
    B_BETTER,
    NO_BENEFIT,
    REFUTED,
    SUPERSEDED,
    SUPPORTED,
    Claim,
)

_LABEL_TEXT = {
    A_BETTER: "intervention better",
    B_BETTER: "baseline better",
    NO_BENEFIT: "no meaningful benefit",
    "inconclusive": "unresolved (inconclusive at the maximum number of seeds)",
}


def _change(claim: Claim) -> str:
    return ", ".join(
        f"`{p}` = {claim.intervention[p]:g} instead of {claim.baseline[p]:g}"
        for p in claim.parameters
    )


def _where(conditions: dict[str, float]) -> str:
    return ", ".join(f"{k}={v:g}" for k, v in sorted(conditions.items()))


def render_report(
    graph: ClaimGraph,
    *,
    title: str = "Claim study",
    study: dict[str, Any] | None = None,
    transfer: dict[str, dict[str, Any]] | None = None,
    composition: list[dict[str, Any]] | None = None,
) -> str:
    """Markdown report: what was claimed, what the simulator said, and how the claims changed."""
    lines = [f"# {title}", ""]
    if study:
        lines += [
            f"{study.get('experiments', '?')} experiments in {study.get('rounds', '?')} rounds, "
            f"{study.get('episodes_used', study.get('episodes_run', '?'))} simulator episodes "
            f"(budget {study.get('budget', '?')}).",
            "",
        ]
    summary = graph.summary()
    lines += [
        f"**{summary['families']} comparisons, {summary['claims']} claims** "
        f"({', '.join(f'{n} {s}' for s, n in sorted(summary['by_status'].items()))}); "
        f"{summary['relations']} relations between claims.",
        "",
    ]
    lines += _policy_map_section(graph)
    lines += ["## Claims by comparison", ""]
    for root in graph.roots():
        author = root.origin.get("author", "?")
        lines += [
            f"### {root.statement}",
            "",
            f"Proposed by: {author}. Compares {_change(root)}.",
            "",
        ]
        lines += [
            "| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |",
            "|---|---|---|---|---|---|",
        ]
        outcome = sorted(
            (e for e in root.evidence if e.kind == "outcome"),
            key=lambda e: tuple(sorted(e.conditions.items())),
        )
        for e in outcome:
            t, c = e.details.get("treatment", {}), e.details.get("control", {})
            fails = f"{sum(t.get('failures', {}).values())} / {sum(c.get('failures', {}).values())}"
            lines.append(
                f"| {_where(e.conditions)} | {_LABEL_TEXT.get(e.label, e.label)} | {e.effect:+.3f} | "
                f"[{e.ci_low:+.3f}, {e.ci_high:+.3f}] | {e.n} | {fails} |"
            )
        lines.append("")
        verdict = {
            SUPPORTED: "Holds everywhere it was tested.",
            REFUTED: "Did not hold anywhere it was tested.",
            SUPERSEDED: "Too general as stated; replaced by the narrower claims below.",
        }.get(root.status, f"Status: {root.status}.")
        lines += [f"**Original claim: {root.status}.** {verdict}", ""]
        for child in graph.children(root.id, active_only=False):
            kind = "reversed" if child.intervention != root.intervention else "narrowed"
            lines.append(
                f"- **{child.status}** ({kind}): where {child.scope.describe()}, use {_change(child)}."
            )
        gaps = False
        for key, text in (
            ("no_benefit_regions", "No meaningful benefit, so nothing is recommended, where: "),
            (
                "unresolved_regions",
                "Not established either way, so nothing is recommended, where: ",
            ),
        ):
            if root.origin.get(key):
                lines.append("- " + text + "; ".join(root.origin[key]) + ".")
                gaps = True
        if graph.children(root.id, active_only=False) or gaps:
            lines.append("")
        if root.mechanisms:
            lines += ["Explanations (judged separately from the outcome):", ""]
            for mechanism in root.mechanisms:
                lines.append(f"- *{mechanism.statement}* — **{mechanism.status}**")
                for e in mechanism.evidence:
                    detail = ""
                    if e.kind == "mediator" and e.details.get("treatment_mean") is None:
                        detail = (
                            f"`{e.details['mediator']}`: {e.details.get('note', 'not evaluated')}"
                        )
                    elif e.kind == "mediator":
                        detail = (
                            f"`{e.details['mediator']}`: {e.details['treatment_mean']:g} with the "
                            f"intervention vs {e.details['control_mean']:g} without"
                            + (" (identical in every seed)" if e.details.get("unmoved") else "")
                            + f", over {e.details.get('pairs_used', e.n)} of "
                            f"{e.details.get('pairs_total', e.n)} seed pairs"
                        )
                    elif e.kind == "moderator":
                        pairs = zip(e.details["levels"], e.details["effect_by_level"], strict=True)
                        detail = f"effect by `{e.details['moderator']}`: " + ", ".join(
                            f"{level:g} -> {effect:+.3f}" for level, effect in pairs
                        )
                    lines.append(
                        f"  - {e.kind} test at {_where(e.conditions)}: {e.verdict}. {detail}"
                    )
            lines.append("")

    lines += ["## Revision history", ""]
    for entry in graph.log:
        if entry["op"] in ("evidence", "mechanism"):
            continue
        lines.append(f"- `{entry['op']}` {entry['claim']}: {entry['detail']}")
    lines.append("")

    for group, result in (transfer or {}).items():
        lines += [
            f"## Transfer: {group}",
            "",
            f"{len(result['test_points'])} conditions never used in an experiment, "
            f"{result['n_seeds']} held-out seeds each.",
            "",
            "| method | mean score | failure rate |",
            "|---|---|---|",
        ]
        for method, row in result["overall"].items():
            lines.append(f"| {method} | {row['mean_score']:+.4f} | {row['failure_rate']:.1%} |")
        lines += ["", "Paired differences over the same (condition, seed) episodes:", ""]
        for name, comparison in result["comparisons"].items():
            sc = comparison["score"]
            lines.append(
                f"- {name.replace('_', ' ')}: {sc['diff']:+.4f} "
                f"[{sc['ci_low']:+.4f}, {sc['ci_high']:+.4f}], p = {sc['p_value']:.4f}"
            )
        lines += ["", "Per condition (mean score, failure rate, settings used):", ""]
        methods = list(result["overall"])
        lines.append("| conditions | " + " | ".join(methods) + " |")
        lines.append("|---|" + "---|" * len(methods))
        for row in result["per_point"]:
            cells = []
            for method in methods:
                m = row["methods"][method]
                settings = (
                    ", ".join(f"{k}={v:g}" for k, v in sorted(m["settings"].items())) or "reference"
                )
                cells.append(f"{m['mean_score']:+.3f} ({m['failure_rate']:.0%}) {settings}")
            lines.append(f"| {_where(row['conditions'])} | " + " | ".join(cells) + " |")
        lines.append("")

    if composition:
        lines += _composition_section(composition)
    return "\n".join(lines)


def _interval(low: float | None, high: float | None) -> str:
    if low is None and high is None:
        return "any"
    if low is None:
        return f"below {high:.4g}"
    if high is None:
        return f"{low:.4g} and above"
    return f"{low:.4g} to {high:.4g}"


def _policy_map_section(graph: ClaimGraph) -> list[str]:
    """The graph's recommendation in each region its supported claims tell apart."""
    from .policy import policy_map

    rows = policy_map(graph)
    parameters = sorted({p for row in rows for p in row["settings"]})
    if not parameters:
        return []
    variables = list(rows[0]["region"].bounds)
    lines = [
        "## What the graph recommends, by condition",
        "",
        "Settings that differ from the reference policy, in every region of conditions the "
        "supported claims tell apart. A dot keeps the reference value: either nothing was "
        "found to beat it there, or nothing could be established."
        + (
            " With more than one condition, a row is the recommendation at one point inside "
            "its region; near the edge of a region the nearest test can decide otherwise."
            if len(variables) > 1
            else ""
        ),
        "",
        "| " + " | ".join(variables + [f"`{p}`" for p in parameters]) + " |",
        "|" + "---|" * (len(variables) + len(parameters)),
    ]
    for row in rows:
        where = [_interval(*row["region"].bounds.get(v, (None, None))) for v in variables]
        values = [f"{row['settings'][p]:g}" if p in row["settings"] else "·" for p in parameters]
        lines.append("| " + " | ".join(where + values) + " |")
    lines.append("")
    return lines


def _finding(row: dict[str, Any]) -> str:
    """The composition verdict of a row, including rows written by earlier versions."""
    if "finding" in row:
        return str(row["finding"])
    return "below best single change" if row.get("interaction") == "negative" else "consistent"


def _composition_section(composition: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Do the recommended settings still work together?",
        "",
        "Every family was tested with only its own change. Here the reference policy, each "
        "recommended change on its own, and all of them together run on the same held-out "
        "seeds.",
        "",
        "| conditions | reference | each change alone | all together | together minus reference "
        "| finding |",
        "|---|---|---|---|---|---|",
    ]
    notes: list[str] = []
    for row in composition:
        where = _where(row["conditions"])
        if "combined_minus_reference" not in row:
            lines.append(f"| {where} | | | | | {row.get('note', 'nothing to combine')} |")
            continue
        d = row["combined_minus_reference"]
        singles = row["single_change_means"]
        alone = "; ".join(f"`{name}` {mean:+.3f}" for name, mean in singles.items())
        finding = _finding(row)
        lines.append(
            f"| {where} | {row['reference_mean']:+.3f} | {alone} | {row['combined_mean']:+.3f} | "
            f"{d['diff']:+.3f} [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}] | {finding} |"
        )
        if finding == "consistent":
            continue
        best = row.get("best_single_change")
        gap = row.get("combined_minus_best_single")
        shortfall = (
            f" All together is {gap['diff']:+.3f} [{gap['ci_low']:+.3f}, {gap['ci_high']:+.3f}] "
            f"against `{best}` alone."
            if best and gap
            else ""
        )
        if finding == "unhelpful change":
            names = ", ".join(
                f"`{name}` ({singles[name]:+.3f} against {row['reference_mean']:+.3f})"
                for name in row.get("unhelpful_alone", [])
            )
            notes.append(
                f"- {where}: on its own, {names} scores below the reference here, so the "
                f"claim behind it is being applied where it does not hold.{shortfall}"
            )
        elif finding == "negative interaction":
            notes.append(
                f"- {where}: every change is at least as good as the reference on its own, "
                f"but together they score below the best of them.{shortfall}"
            )
        else:
            notes.append(f"- {where}: the combination scores below its best single change.")
    lines.append("")
    if notes:
        lines += notes + [""]
    return lines
