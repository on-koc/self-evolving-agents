"""Figures for a claim study (needs the ``plots`` extra: matplotlib).

Two figures, both static PNGs for documents:

* ``plot_claims``   – one small panel per comparison: the measured effect at every
  tested condition, with its interval, and the regions in which the graph ended up
  recommending the intervention, the baseline, or nothing.
* ``plot_transfer`` – mean score of each way of using the graph at each held-out
  condition, with the claim graph's result emphasised.

The numbers behind both are in the study's ``report.md``, which is the table view of
these figures. Colours: the blue/red pair was checked for colour-vision separation
(CVD dE 21.6, normal-vision dE 32.3, both at least 3:1 against the surface), and every
distinction drawn in colour is also drawn in marker shape.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .graph import ClaimGraph
from .schema import A_BETTER, B_BETTER, INCONCLUSIVE, NO_BENEFIT, SUPPORTED, Claim

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"  # the intervention did better
RED = "#e34948"  # the baseline did better

_STYLE = {
    A_BETTER: dict(marker="^", color=BLUE, filled=True, label="intervention better"),
    B_BETTER: dict(marker="v", color=RED, filled=True, label="baseline better"),
    NO_BENEFIT: dict(marker="o", color=INK_MUTED, filled=False, label="no meaningful benefit"),
    INCONCLUSIVE: dict(marker="D", color=INK_MUTED, filled=False, label="unresolved"),
}


def _pyplot() -> Any:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - depends on the optional extra
        raise ImportError(
            "plots need matplotlib: pip install 'self-evolving-agents[plots]'"
        ) from exc
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.edgecolor": AXIS,
            "axes.linewidth": 0.8,
            "axes.labelcolor": INK_SECONDARY,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
        }
    )
    return plt


def _tidy(ax: Any) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.set_axisbelow(True)


def _short(claim: Claim) -> str:
    return ", ".join(
        f"{p} {claim.intervention[p]:g} vs {claim.baseline[p]:g}" for p in claim.parameters
    )


def _setting(values: dict[str, float]) -> str:
    return ", ".join(f"{p} = {v:g}" for p, v in sorted(values.items()))


def plot_claims(
    graph: ClaimGraph,
    path: str | Path,
    *,
    x: str,
    x_label: str | None = None,
    fixed: dict[str, float] | None = None,
    title: str = "",
) -> Path:
    """Effect of each comparison against one condition, with the graph's verdict per region.

    ``fixed`` selects a slice when the study explored more than one condition: only
    evidence whose other conditions equal these values is drawn.
    """
    plt = _pyplot()
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    fixed = fixed or {}
    families = []
    for root in graph.roots():
        points = [
            e
            for e in root.evidence
            if e.kind == "outcome"
            and x in e.conditions
            and all(e.conditions.get(k) == v for k, v in fixed.items())
        ]
        if points:
            families.append((root, sorted(points, key=lambda e: e.conditions[x])))
    if not families:
        raise ValueError("no outcome evidence to plot for this slice")

    all_x = [e.conditions[x] for _, points in families for e in points]
    x_min, x_max = min(all_x) / 1.25, max(all_x) * 1.25
    cols = 2 if len(families) > 1 else 1
    rows = math.ceil(len(families) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(4.7 * cols, 2.45 * rows + 0.9), squeeze=False)

    for ax, (root, points) in zip(axes.flat, families, strict=False):
        _tidy(ax)
        ax.set_xscale("log")
        ax.set_xlim(x_min, x_max)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.axhline(0, color=AXIS, linewidth=1.0, zorder=1)

        # Regions in which a claim of this family is currently supported.
        regions = []
        for claim in graph.active(root.id):
            if claim.status != SUPPORTED:
                continue
            slice_ok = all(
                (low is None or fixed[var] >= low) and (high is None or fixed[var] < high)
                for var, (low, high) in claim.scope.bounds.items()
                if var in fixed
            )
            if not slice_ok:
                continue
            low, high = claim.scope.bounds.get(x, (None, None))
            low, high = max(low or x_min, x_min), min(high or x_max, x_max)
            if low >= high:
                continue
            same = claim.intervention == root.intervention
            ax.axvspan(low, high, color=BLUE if same else RED, alpha=0.10, linewidth=0, zorder=0)
            regions.append((low, high, claim))

        for e in points:
            style = _STYLE.get(e.label, _STYLE[INCONCLUSIVE])
            xv = e.conditions[x]
            ax.plot(
                [xv, xv],
                [e.ci_low, e.ci_high],
                color=style["color"],
                linewidth=1.5,
                solid_capstyle="round",
                zorder=2,
            )
            ax.plot(
                [xv],
                [e.effect],
                marker=style["marker"],
                linestyle="none",
                # A filled mark loses its ring to the surface colour, so it is drawn larger.
                markersize=10 if style["filled"] else 7.5,
                markerfacecolor=style["color"] if style["filled"] else SURFACE,
                markeredgecolor=SURFACE if style["filled"] else style["color"],
                markeredgewidth=1.6,
                zorder=3,
            )

        # Name each region's recommendation where the text fits; the legend covers the rest.
        low_y, high_y = ax.get_ylim()
        pad = 0.16 * (high_y - low_y)
        ax.set_ylim(low_y, high_y + pad)
        span = math.log(x_max / x_min)
        for low, high, claim in regions:
            text = "use " + _setting(claim.intervention)
            if math.log(high / low) / span * 4.7 * 72 < 5.2 * len(text) + 10:
                continue  # too narrow for the label
            ax.text(
                math.sqrt(low * high),
                high_y + pad * 0.42,
                text,
                ha="center",
                va="center",
                fontsize=7.5,
                color=INK_SECONDARY,
            )

        ax.set_title(_short(root), loc="left", fontsize=9.5, color=INK, pad=6)
        ticks = sorted({v for v in all_x if v in (10, 25, 50, 100, 200, 400, 800, 1600)}) or None
        if ticks:
            ax.set_xticks(ticks)
            ax.set_xticklabels([f"{v:g}" for v in ticks])
        ax.minorticks_off()
        ax.set_ylabel("effect on score")
    for ax in axes.flat[len(families) :]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel(x_label or x)

    handles = [
        Line2D(
            [],
            [],
            marker=s["marker"],
            linestyle="none",
            markersize=10 if s["filled"] else 7.5,
            markerfacecolor=s["color"] if s["filled"] else SURFACE,
            markeredgecolor=SURFACE if s["filled"] else s["color"],
            markeredgewidth=1.6,
            label=s["label"],
        )
        for s in _STYLE.values()
    ]
    handles += [
        Patch(
            facecolor=BLUE, alpha=0.18, edgecolor="none", label="graph recommends the intervention"
        ),
        Patch(facecolor=RED, alpha=0.18, edgecolor="none", label="graph recommends the baseline"),
    ]
    fig.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.012, 0.985),
        ncol=3,
        frameon=False,
        fontsize=8,
        labelcolor=INK_SECONDARY,
        handletextpad=0.5,
        columnspacing=1.6,
    )
    if title:
        fig.suptitle(title, x=0.012, y=1.0, ha="left", va="bottom", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.75 / (2.45 * rows + 0.9)))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


_METHODS = {
    "reference": dict(marker="o", label="reference policy"),
    "flat": dict(marker="s", label="flat lessons"),
    "pooled": dict(marker="^", label="best single setting"),
    "conditional": dict(marker="o", label="claim graph"),
    "oracle": dict(marker="|", label="oracle (ceiling)"),
}


def plot_transfer(
    transfer: dict[str, dict[str, Any]], path: str | Path, *, title: str = ""
) -> Path:
    """Mean held-out score of each method at each held-out condition, claim graph emphasised."""
    plt = _pyplot()
    from matplotlib.lines import Line2D

    groups = list(transfer.items())
    heights = [len(result["per_point"]) for _, result in groups]
    fig, axes = plt.subplots(
        len(groups),
        1,
        figsize=(7.4, 0.52 * sum(heights) + 1.15 * len(groups) + 0.7),
        sharex=True,
        squeeze=False,
        gridspec_kw={"height_ratios": heights},
    )
    for ax, (group, result) in zip(axes[:, 0], groups, strict=True):
        _tidy(ax)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.axvline(0, color=AXIS, linewidth=1.0, zorder=1)
        rows = result["per_point"]
        labels = []
        for i, row in enumerate(rows):
            y = len(rows) - 1 - i
            labels.append(
                ", ".join(f"{k.split('_')[0]} {v:g}" for k, v in sorted(row["conditions"].items()))
            )
            scores = {m: row["methods"][m]["mean_score"] for m in _METHODS if m in row["methods"]}
            ax.plot(
                [min(scores.values()), max(scores.values())],
                [y, y],
                color=GRID,
                linewidth=2,
                solid_capstyle="round",
                zorder=1,
            )
            for method, score in scores.items():
                style = _METHODS[method]
                if method == "conditional":
                    ax.plot(
                        [score],
                        [y],
                        marker="o",
                        markersize=9.5,
                        linestyle="none",
                        markerfacecolor=BLUE,
                        markeredgecolor=SURFACE,
                        markeredgewidth=1.6,
                        zorder=4,
                    )
                    ax.annotate(
                        f"{score:+.2f}",
                        (score, y),
                        textcoords="offset points",
                        xytext=(0, 9),
                        ha="center",
                        fontsize=7.5,
                        color=INK_SECONDARY,
                    )
                elif method == "oracle":
                    ax.plot(
                        [score],
                        [y],
                        marker="|",
                        markersize=13,
                        linestyle="none",
                        markeredgecolor=INK,
                        markeredgewidth=1.6,
                        zorder=3,
                    )
                else:
                    ax.plot(
                        [score],
                        [y],
                        marker=style["marker"],
                        markersize=7.5,
                        linestyle="none",
                        markerfacecolor=INK_MUTED,
                        markeredgecolor=SURFACE,
                        markeredgewidth=1.4,
                        zorder=2,
                    )
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels(labels[::-1], color=INK_SECONDARY)
        ax.set_ylim(-0.6, len(rows) - 0.25)
        ax.set_title(group, loc="left", fontsize=9.5, color=INK, pad=6)
    axes[-1, 0].set_xlabel(
        "mean score on held-out seeds (1 = recording all the time, below 0 = spacecraft lost)"
    )

    present = [
        m for m in _METHODS if any(m in row["methods"] for _, r in groups for row in r["per_point"])
    ]
    handles = []
    for method in present:
        style = _METHODS[method]
        if method == "conditional":
            handles.append(
                Line2D(
                    [],
                    [],
                    marker="o",
                    linestyle="none",
                    markersize=9,
                    markerfacecolor=BLUE,
                    markeredgecolor=SURFACE,
                    markeredgewidth=1.6,
                    label=style["label"],
                )
            )
        elif method == "oracle":
            handles.append(
                Line2D(
                    [],
                    [],
                    marker="|",
                    linestyle="none",
                    markersize=12,
                    markeredgecolor=INK,
                    markeredgewidth=1.6,
                    label=style["label"],
                )
            )
        else:
            handles.append(
                Line2D(
                    [],
                    [],
                    marker=style["marker"],
                    linestyle="none",
                    markersize=7.5,
                    markerfacecolor=INK_MUTED,
                    markeredgecolor=SURFACE,
                    markeredgewidth=1.4,
                    label=style["label"],
                )
            )
    fig.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.012, 0.99),
        ncol=len(handles),
        frameon=False,
        fontsize=8,
        labelcolor=INK_SECONDARY,
        handletextpad=0.4,
        columnspacing=1.4,
    )
    if title:
        fig.suptitle(title, x=0.012, y=1.0, ha="left", va="bottom", fontsize=11, color=INK)
    total = 0.52 * sum(heights) + 1.15 * len(groups) + 0.7
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.42 / total))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path
