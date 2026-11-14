"""Claims from a claim graph, rendered as memory items for a language-model agent."""

from __future__ import annotations

import math

from ..claim_graph.graph import ClaimGraph
from ..claim_graph.schema import CONTRADICTS, SUPPORTED, SUPPORTS, Claim
from ..reasoningbank.schema import MemoryItem

SOURCE_CLAIM = "claim"  # rendered from a claim that was tested in simulation


def _change(claim: Claim) -> str:
    return ", ".join(
        f"`{p}` = {claim.intervention[p]:g} instead of {claim.baseline[p]:g}"
        for p in claim.parameters
    )


def _where(conditions: dict[str, float]) -> str:
    return ", ".join(f"{k}={v:g}" for k, v in sorted(conditions.items()))


def claims_as_memory(
    graph: ClaimGraph, conditions: dict[str, float], *, max_items: int = 8
) -> list[MemoryItem]:
    """Render the claims that apply under ``conditions`` as memory items.

    Each item says what to do, where that has actually been tested, how far the
    current conditions are from the nearest supporting test, and what is known about
    why it works, so the agent can weigh a well-tested rule differently from an
    extrapolated one. The scope goes into the description, so these items have to be
    shown with their description.
    """
    items = []
    applicable = sorted(graph.applicable(conditions, statuses=(SUPPORTED,)), key=lambda x: x[1])
    for claim, distance in applicable[:max_items]:
        root = graph.root(claim)
        same_direction = claim.intervention == root.intervention
        supporting = [e for e in claim.outcome_evidence() if e.verdict == SUPPORTS]
        beyond = [
            e
            for e in claim.evidence
            if e.kind == "outcome"
            and e.verdict == CONTRADICTS
            and not claim.scope.contains(e.conditions)
        ]
        best = max(supporting, key=lambda e: e.ci_low) if supporting else None
        if distance == 0:
            footing = "It was tested under exactly these conditions."
        elif distance == float("inf"):
            footing = "It has no supporting test yet."
        else:
            footing = (
                f"The nearest supporting test differs from the current conditions by a factor of "
                f"about {math.exp(distance):.2f}; treat it as an extrapolation."
            )
        if same_direction:
            title = claim.statement
        else:
            title = f"Here the opposite of this holds: {root.statement}"
        content = f"Use {_change(claim)}. "
        if best is not None:
            content += (
                f"In a matched-seed test at {_where(best.conditions)} this changed the score by "
                f"{best.effect:+.3f} (interval {best.ci_low:+.3f} to {best.ci_high:+.3f}, "
                f"{best.n} seeds). "
            )
        if beyond:
            content += (
                "Outside the stated range it did not hold (tested at "
                + "; ".join(_where(e.conditions) for e in beyond[:4])
                + "). "
            )
        if same_direction:
            # The explanations were given for the original direction of the claim only.
            for mechanism in root.mechanisms:
                content += f"Explanation '{mechanism.statement}' is {mechanism.status}. "
        items.append(
            MemoryItem(
                title=title[:160],
                description=f"Applies where {claim.scope.describe()}. {footing}",
                content=content.strip(),
                source=SOURCE_CLAIM,
                meta={
                    "claim_id": claim.id,
                    "distance": None if distance == float("inf") else distance,
                },
            )
        )
    return items
