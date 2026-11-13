"""Where hypotheses come from: files written by people, and a language model.

Whatever the source, a hypothesis enters the graph in the same structured form and
with the same status, ``hypothesis``. Nothing a person or a model writes here is
believed until the simulator has tested it; the author is recorded so that it stays
clear who proposed what.

Specification format (JSON object)::

    {
      "statement": "A lower charge threshold collects more data.",
      "intervention": {"charge_below": 0.10},
      "baseline": {"charge_below": 0.25},            # optional: defaults to the reference setting
      "scope": {"battery_capacity_wh": [100, null]},  # optional: [low, high), null = open
      "context": {"battery_capacity_wh": 200},        # optional: where to test it first
      "min_effect": 0.02,                             # optional
      "mechanisms": [                                 # optional explanations
        {"statement": "less time is spent charging",
         "mediator": "time_charge_s", "mediator_direction": -1,
         "moderator": "panel_area_m2", "moderator_direction": -1}
      ]
    }
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ...envs.scanning import DEFAULT_CONDITIONS
from ...llm import LLMRequest, user
from ...llm.parsing import extract_json_object
from ...policies import SCAN_POLICY_DEFAULTS, SCAN_POLICY_KNOBS
from .graph import ClaimGraph
from .schema import Claim, Mechanism, Region
from .testing import Domain


class HypothesisError(ValueError):
    """A hypothesis specification is malformed or refers to unknown names."""


def claim_from_spec(
    spec: dict[str, Any],
    *,
    env_id: str = "bsk-scan",
    author: str = "human",
    knobs: dict[str, float] | None = None,
    conditions: Sequence[str] | None = None,
) -> Claim:
    """Validate a hypothesis specification and turn it into a claim."""
    knobs = dict(knobs if knobs is not None else SCAN_POLICY_DEFAULTS)
    known_conditions = set(conditions if conditions is not None else DEFAULT_CONDITIONS)
    if not isinstance(spec, dict):
        raise HypothesisError("a hypothesis must be a JSON object")
    statement = str(spec.get("statement", "")).strip()
    if not statement:
        raise HypothesisError("missing 'statement'")
    intervention = spec.get("intervention")
    if not isinstance(intervention, dict) or not intervention:
        raise HypothesisError("'intervention' must set at least one policy parameter")
    unknown = set(intervention) - set(knobs)
    if unknown:
        raise HypothesisError(f"unknown policy parameter(s): {', '.join(sorted(unknown))}")
    baseline = spec.get("baseline") or {p: knobs[p] for p in intervention}
    if set(baseline) != set(intervention):
        raise HypothesisError("'baseline' must set the same parameters as 'intervention'")
    try:
        intervention = {p: float(v) for p, v in intervention.items()}
        baseline = {p: float(v) for p, v in baseline.items()}
    except (TypeError, ValueError):
        raise HypothesisError("parameter values must be numbers") from None

    bounds: dict[str, tuple[float | None, float | None]] = {}
    for var, pair in (spec.get("scope") or {}).items():
        if var not in known_conditions:
            raise HypothesisError(f"unknown condition in scope: {var}")
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise HypothesisError(f"scope of {var} must be [low, high]")
        low, high = (None if x is None else float(x) for x in pair)
        if low is not None and high is not None and low >= high:
            raise HypothesisError(f"scope of {var} is empty")
        bounds[var] = (low, high)
    context = {k: float(v) for k, v in (spec.get("context") or {}).items()}
    unknown = set(context) - known_conditions
    if unknown:
        raise HypothesisError(f"unknown condition in context: {', '.join(sorted(unknown))}")

    mechanisms = []
    for m in spec.get("mechanisms") or []:
        if not isinstance(m, dict) or not str(m.get("statement", "")).strip():
            raise HypothesisError("each mechanism needs a 'statement'")
        directions = (int(m.get("mediator_direction", 0)), int(m.get("moderator_direction", 0)))
        if any(d not in (-1, 0, 1) for d in directions):
            raise HypothesisError("directions must be -1, 0 or 1")
        moderator = m.get("moderator")
        if moderator is not None and moderator not in known_conditions:
            raise HypothesisError(f"unknown moderator condition: {moderator}")
        mechanisms.append(
            Mechanism(
                statement=str(m["statement"]).strip(),
                mediator=m.get("mediator"),
                mediator_direction=directions[0],
                moderator=moderator,
                moderator_direction=directions[1],
            )
        )
    try:
        return Claim(
            statement=statement,
            intervention=intervention,
            baseline=baseline,
            scope=Region(bounds),
            metric=str(spec.get("metric", "score")),
            min_effect=float(spec.get("min_effect", 0.02)),
            mechanisms=mechanisms,
            env_id=env_id,
            origin={
                "author": spec.get("author", author),
                "context": context,
                "note": str(spec.get("note", "")) or f"proposed by {spec.get('author', author)}",
            },
        )
    except ValueError as exc:
        raise HypothesisError(str(exc)) from None


def load_hypotheses(path: str | Path, **kwargs: Any) -> list[Claim]:
    """Read a JSON file holding a list of hypothesis specifications."""
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list):
        raise HypothesisError("the file must contain a JSON list of hypotheses")
    return [claim_from_spec(spec, **kwargs) for spec in data]


def graph_digest(graph: ClaimGraph, limit: int = 30) -> str:
    """Compact account of what the graph currently holds, for a proposer's prompt."""
    lines = []
    for root in graph.roots()[:limit]:
        lines.append(f"- {root.describe()}")
        for e in [e for e in root.evidence if e.kind == "outcome"][-6:]:
            lines.append(f"    test: {e.label} ({e.summary()})")
        for mechanism in root.mechanisms:
            lines.append(f"    explanation [{mechanism.status}]: {mechanism.statement}")
        for child in graph.children(root.id):
            lines.append(f"    -> {child.describe()}")
    return "\n".join(lines) if lines else "(no claims yet)"


PROPOSER_SYSTEM = """\
You are an expert in {domain}. You help run a programme of simulation experiments whose \
purpose is to learn which operating strategies work under which conditions.

A strategy is a setting of the parameters of a fixed decision policy. A hypothesis says that, \
within some range of operating conditions, one setting beats another. Every hypothesis you \
propose will be tested in the simulator on matched random seeds, so propose things whose test \
would be informative: a setting you expect to help, a condition under which an accepted claim \
might stop holding, or a competing explanation for a result already in the record.

Keep two things apart. What a test showed is recorded for you below. Why it came out that way \
is not known from the outcome alone. When you give an explanation, state it as something that \
can be checked: name a measured quantity that should move if the explanation is right (the \
mediator) and, if you can, a condition that should make the effect stronger or weaker (the \
moderator).

## The policy and its parameters
{policy}

Parameters and their reference values:
{knobs}

## Operating conditions that can be varied
{conditions}

## Quantities measured in every episode (usable as mediators)
{metrics}

## Output
Reply with a short explanation of your thinking, then a ```json code block holding a list of at \
most {n} hypotheses, each an object with:
- "statement": one sentence.
- "intervention": parameter settings to try.
- "baseline": the settings to compare against (omit to compare with the reference values).
- "scope": optional. Conditions under which you expect it to hold, as {{"condition": [low, high]}} \
with null for an open side.
- "context": optional. The condition values at which to test it first.
- "mechanisms": optional list of {{"statement", "mediator", "mediator_direction" (-1 or 1), \
"moderator", "moderator_direction" (-1 or 1)}}.
"""

SCAN_METRICS = {
    "score": "total reward: fraction of the episode spent recording, minus 1 if the spacecraft was lost",
    "failure:battery": "1 if the battery was fully depleted",
    "failure:wheels": "1 if a reaction wheel exceeded its speed limit",
    "min_battery": "lowest battery fraction reached",
    "max_wheel_speed": "highest wheel-speed fraction reached",
    "mode_switches": "number of times the operating mode changed",
    "wasted_scan_s": "seconds spent in scan mode that recorded nothing",
    "dark_charge_s": "seconds spent in charge mode that began in eclipse",
    "time_scan_s": "seconds in scan mode",
    "time_charge_s": "seconds in charge mode",
    "time_downlink_s": "seconds in downlink mode",
    "time_desat_s": "seconds in desat mode",
}


class LLMProposer:
    """Asks a language model for new hypotheses, given the graph and recent episodes.

    The model only proposes. Each proposal is validated against the known parameters
    and conditions; ones that do not validate are dropped and listed in
    ``self.rejected`` with the reason. Accepted proposals enter the graph as
    hypotheses authored by ``llm:<model>`` and wait for the simulator.
    """

    def __init__(
        self,
        llm: Any,
        domain: Domain,
        *,
        policy_text: str,
        domain_name: str = "spacecraft operations and satellite tasking",
        max_hypotheses: int = 4,
        every: int = 1,
        notes: str = "",
    ):
        self.llm = llm
        self.domain = domain
        self.policy_text = policy_text
        self.domain_name = domain_name
        self.max_hypotheses = max_hypotheses
        self.every = max(1, every)
        self.notes = notes
        self.calls = 0
        self.rejected: list[dict[str, str]] = []

    def system_prompt(self) -> str:
        return PROPOSER_SYSTEM.format(
            domain=self.domain_name,
            policy=self.policy_text,
            knobs="\n".join(
                f"- {k} = {SCAN_POLICY_DEFAULTS[k]:g}: {doc}"
                for k, doc in SCAN_POLICY_KNOBS.items()
            ),
            conditions="\n".join(
                f"- {var} (reference {self.domain.reference[var]:g})"
                + (f"; studied at {levels}" if (levels := self.domain.variables.get(var)) else "")
                for var in sorted(self.domain.reference)
            ),
            metrics="\n".join(f"- {k}: {doc}" for k, doc in SCAN_METRICS.items()),
            n=self.max_hypotheses,
        )

    def propose(self, graph: ClaimGraph) -> list[Claim]:
        self.calls += 1
        if (self.calls - 1) % self.every:
            return []
        prompt = "## What the record holds so far\n" + graph_digest(graph)
        if self.notes:
            prompt += "\n\n## Observations from recent episodes\n" + self.notes
        prompt += "\n\nPropose the next hypotheses to test."
        response = self.llm.complete(
            LLMRequest(system=self.system_prompt(), messages=[user(prompt)], purpose="propose")
        )
        try:
            start, end = response.text.find("["), response.text.rfind("]")
            if "```" in response.text:
                fenced = response.text.split("```")[1]
                payload = fenced[4:] if fenced.startswith("json") else fenced
            else:
                payload = response.text[start : end + 1]
            specs = json.loads(payload)
            if isinstance(specs, dict):
                specs = [specs]
        except (ValueError, IndexError):
            try:
                specs = [extract_json_object(response.text)]
            except ValueError as exc:
                self.rejected.append(
                    {"reason": f"reply was not JSON: {exc}", "spec": response.text[:200]}
                )
                return []
        claims = []
        for spec in specs[: self.max_hypotheses]:
            try:
                claim = claim_from_spec(
                    spec,
                    env_id=self.domain.env_id,
                    author=f"llm:{self.llm.model}",
                    conditions=list(self.domain.reference),
                )
            except HypothesisError as exc:
                self.rejected.append({"reason": str(exc), "spec": json.dumps(spec)[:300]})
                continue
            claim.origin["author"] = f"llm:{self.llm.model}"
            claim.origin["llm_call_id"] = response.call_id
            claim.origin["note"] = f"proposed by {self.llm.model}"
            claims.append(claim)
        return claims
