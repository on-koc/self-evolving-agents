"""Investigative behaviours: what counts, and how each is detected.

Five behaviours are measured. Each has an operational definition, and where an
episode's actions can show it, a detector that reads only the actions and their
results (no model, so no judgement to doubt). Where only the agent's reasoning can
show it, a model codes the episode, blind to the method that produced it.

==================  ===============================================  =======================
Behaviour           Operational definition                           Detected from
==================  ===============================================  =======================
controls            a measurement or test of a reference case:       actions, for Archaeology
                    something whose answer is known, or a condition  (known-age artifacts) and
                    where the factor under test is absent            Reactor Lab (known
                                                                     crystals); coding elsewhere
alternatives        two or more candidates tested before the final   actions: distinct
                    answer was committed                             candidates tested before
                                                                     the commit; coding
confounds           a step that removes a competing explanation of   actions, for Combinatorial
                    a result, or reasoning that names one            Chemistry (cleaning the jar
                                                                     between different tests);
                                                                     coding
revision            after an observation that contradicted a held    actions, for Combinatorial
                    belief, the belief is dropped and behaviour      Chemistry (a failed test is
                    changes accordingly                              followed by a different
                                                                     one, not repeated); coding
transfer            a strategy formed in earlier tasks is used in a  design: transfer tasks,
                    new one                                          lesions, citation of
                                                                     retrieved strategies
==================  ===============================================  =======================

The coder's own accuracy has to be checked against people before its codes are
reported (``sea discovery code-sample`` exports episodes for that; ``sea discovery
agreement`` computes Cohen's kappa). Until then, only the action detectors are
results.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..llm import LLMRequest, extract_json_object, user
from ..types import Trajectory

INSTRUMENT_WORDS = (
    "meter",
    "microscope",
    "spectrometer",
    "densitometer",
    "thermometer",
    "npk field test",
    "sampler",
)
COMMITTING = ("PUT", "DROP", "USE", "ACTIVATE", "DIALOG", "OPEN")
_KEY_STATE = re.compile(r"\]\s*(?:rusted\s+)?key \(([^)]*)\)")
_SUBSTANCE = re.compile(r"Dispenser \(Substance ([A-Z])\)")


def _names(step: Any) -> tuple[str, str]:
    names = step.info.get("arg_names") or {}
    return str(names.get("arg1") or "").lower(), str(names.get("arg2") or "").lower()


def _action(step: Any) -> dict[str, Any]:
    try:
        value = json.loads(step.action)
        return value if isinstance(value, dict) else {"action": step.action}
    except (json.JSONDecodeError, TypeError):
        return {"action": step.action}


def is_instrument(name: str) -> bool:
    return any(word in name for word in INSTRUMENT_WORDS)


def measurements(traj: Trajectory) -> list[dict[str, Any]]:
    """Every use of an instrument on something, with the step and whether it worked."""
    out = []
    for step in traj.steps:
        action = _action(step)
        if action.get("action") != "USE":
            continue
        tool, target = _names(step)
        if is_instrument(tool) and target:
            out.append(
                {
                    "step": step.index,
                    "instrument": tool,
                    "target": target,
                    "target_id": action.get("arg2"),
                    "ok": bool(step.info.get("action_ok")),
                }
            )
    return out


def commit_step(traj: Trajectory) -> int | None:
    """The step that completed the task (its irreversible final action), if any."""
    if traj.outcome is None or not traj.outcome.terminated or not traj.steps:
        return None
    return traj.steps[-1].index


# --------------------------------------------------------------------------- per theme


def chemistry_tests(traj: Trajectory) -> list[dict[str, Any]]:
    """Combinatorial Chemistry: every time the key went into the jar, what the jar held.

    Jar contents are tracked from the actions: a dispenser used on the jar adds its
    substance, the bottle cleaner empties it. The key's state is read from the
    observations that follow ("key (no rust)").
    """
    contents: list[str] = []
    cleaned_since_test = True
    tests: list[dict[str, Any]] = []
    steps = traj.steps
    for i, step in enumerate(steps):
        action = _action(step)
        verb = action.get("action")
        tool, target = _names(step)
        ok = bool(step.info.get("action_ok"))
        if verb == "USE" and ok and "jar" in target:
            match = _SUBSTANCE.search((step.info.get("arg_names") or {}).get("arg1") or "")
            if match:
                contents.append(match.group(1))
            elif "cleaner" in tool or "washer" in tool:
                contents = []
                cleaned_since_test = True
        elif verb == "PUT" and ok and "key" in tool and "jar" in target:
            state = None
            for later in steps[i + 1 : i + 4]:
                found = _KEY_STATE.findall(later.observation)
                if found:
                    state = found[0]
                    break
            if state is None:
                found = _KEY_STATE.findall(traj.final_observation or "")
                state = found[0] if found else None
            tests.append(
                {
                    "step": step.index,
                    "contents": sorted(set(contents)),
                    "parts": sorted(contents),
                    "after": state,
                    "worked": state is not None and "no rust" in state,
                    "cleaned_before": cleaned_since_test,
                }
            )
            cleaned_since_test = False
    return tests


def _known_crystals(query: str) -> set[str]:
    """Reactor Lab: the crystals whose frequencies the task says are known."""
    if "correct frequencies for" not in query:
        return set()
    listed = query.split("correct frequencies for", 1)[1].split("which are", 1)[0]
    return set(re.findall(r"Crystal (\d)", listed))


# --------------------------------------------------------------------------- detectors


def detect(traj: Trajectory) -> dict[str, Any]:
    """Action-level indicators of the five behaviours for one episode."""
    scenario = str(traj.task.conditions.get("scenario", ""))
    difficulty = str(traj.task.conditions.get("difficulty", ""))
    measured = measurements(traj)
    commit = commit_step(traj)
    before = [m for m in measured if commit is None or m["step"] < commit]
    pairs: dict[tuple[str, Any], int] = {}
    for m in measured:
        key = (m["instrument"], m["target_id"])
        pairs[key] = pairs.get(key, 0) + 1
    out: dict[str, Any] = {
        "scenario": scenario,
        "difficulty": difficulty,
        "steps": len(traj.steps),
        "completed": bool(traj.outcome and traj.outcome.terminated),
        "success": bool(traj.outcome and traj.outcome.success),
        "commit_step": commit,
        "measurements": len(measured),
        "distinct_targets": len({m["target_id"] for m in measured}),
        "distinct_instruments": len({m["instrument"] for m in measured}),
        "repeated_measurements": sum(1 for count in pairs.values() if count > 1),
        "candidates_before_commit": len({m["target_id"] for m in before}),
        "controls": None,
        "alternatives": None,
        "confounds": None,
        "revision": None,
    }
    if scenario == "Combinatorial Chemistry":
        tests = chemistry_tests(traj)
        tested = [t for t in tests if commit is None or t["step"] <= commit]
        distinct = {tuple(t["parts"]) for t in tested}
        failed = [i for i, t in enumerate(tests) if not t["worked"]]
        followed = [i for i in failed if i + 1 < len(tests)]
        changed = [i for i in followed if tests[i + 1]["parts"] != tests[i]["parts"]]
        switches = [
            i
            for i in range(1, len(tests))
            if set(tests[i]["contents"]) != set(tests[i - 1]["contents"])
        ]
        clean_switches = [i for i in switches if tests[i]["cleaned_before"]]
        out.update(
            tests=len(tests),
            distinct_tests=len(distinct),
            first_test=tests[0]["contents"] if tests else None,
            first_working_test=next((i for i, t in enumerate(tests) if t["worked"]), None),
            contaminated_tests=sum(1 for i in switches if not tests[i]["cleaned_before"]),
            repeated_failed_tests=len(followed) - len(changed),
            alternatives=len(distinct) >= 2,
            confounds=(len(clean_switches) / len(switches)) if switches else None,
            revision=(len(changed) / len(followed)) if followed else None,
        )
        out["candidates_before_commit"] = len(distinct)
    else:
        out["alternatives"] = out["candidates_before_commit"] >= 2
    if scenario == "Archaeology Dating" and difficulty == "Challenge":
        known = {
            m["target_id"]
            for m in measured
            if any(w in m["target"] for w in ("stone", "bronze", "iron"))
        }
        out["controls"] = len(known) > 0
        out["reference_measurements"] = len(known)
    if scenario == "Reactor Lab":
        numbers = _known_crystals(traj.query)
        known = {
            m["target_id"]
            for m in measured
            if any(m["target"].endswith(f"crystal {n}") for n in numbers)
        }
        out["controls"] = len(known) > 0 if numbers else None
        out["reference_measurements"] = len(known)
    out["premature_commit"] = commit is not None and out["candidates_before_commit"] <= 1
    return out


# --------------------------------------------------------------------------- coding

BEHAVIOUR_DEFINITIONS = {
    "control": (
        "The agent compared a case under test with a reference case in which the factor under "
        "test was absent, already known, or held fixed (for example, measuring something of "
        "known value alongside unknown ones, or a test with nothing added)."
    ),
    "alternatives": (
        "Before committing to a final answer, the agent tested at least two candidate answers or "
        "explanations, or gathered evidence that distinguishes between candidates it named."
    ),
    "confound": (
        "The agent named a possible confounding variable (another difference that could explain "
        "a result) or acted to remove one (for example, emptying or cleaning equipment between "
        "tests, or changing one factor at a time)."
    ),
    "revision": (
        "After an observation that contradicted a belief or hypothesis the agent held, the agent "
        "dropped or changed that belief and acted on the change."
    ),
    "premature_commitment": (
        "The agent committed to a final answer without testing it, or without testing any "
        "alternative."
    ),
}

CODER_SYSTEM = """\
You are coding the record of an attempt at a scientific task, for a study of how \
investigators work. Read the record and decide, for each behaviour below, whether it \
occurred in this attempt. Base every decision only on the record. If a behaviour \
occurred, give the step number that shows it and quote the words or the action.

Behaviours:
%s

Answer with one JSON object and nothing else, with one entry per behaviour:
{"control": {"present": false, "step": null, "evidence": ""}, ...}"""

#: Sentences that would tell the coder whether the agent had a memory.
_REDACT = re.compile(
    r"[^.!?\n]*\b(?:memory|memories|notes? from|earlier (?:task|investigation|attempt)s?|"
    r"previous (?:task|investigation|attempt|world)s?|strateg(?:y|ies) S\d+|S\d+\b)[^.!?\n]*[.!?]?",
    flags=re.IGNORECASE,
)


def redact(text: str) -> str:
    """Remove sentences that mention memory or earlier tasks, so coding stays blind."""
    return _REDACT.sub(" [sentence removed] ", text)


def coding_record(traj: Trajectory, max_chars: int = 30000) -> str:
    lines = [f"Task: {traj.query}", ""]
    for step in traj.steps:
        thought = redact(" ".join((step.thought or "").split()))[:500]
        names = step.info.get("arg_names") or {}
        what = step.action
        if names:
            what += " (" + ", ".join(f"{k} = {v}" for k, v in names.items() if v) + ")"
        line = f"Step {step.index}: {what} -> {' '.join(step.result.split())[:300]}"
        if thought:
            line = f"Step {step.index}: reasoning: {thought} | " + line.split(": ", 1)[1]
        lines.append(line)
    notes = traj.meta.get("scientific_knowledge")
    if notes:
        lines += ["", "Notes the agent kept:", redact(json.dumps(notes, indent=1))[:8000]]
    text = "\n".join(lines)
    if len(text) > max_chars:
        half = max_chars // 2
        text = text[:half] + "\n[... middle omitted ...]\n" + text[-half:]
    return text


class BehaviourCoder:
    """A model codes an episode for the behaviours, from a record with memory redacted."""

    def __init__(self, llm: Any, *, temperature: float = 0.0, max_tokens: int = 1500):
        self.llm = llm
        self.temperature = temperature
        self.max_tokens = max_tokens

    def code(self, traj: Trajectory) -> dict[str, Any]:
        listing = "\n".join(f'- "{k}": {v}' for k, v in BEHAVIOUR_DEFINITIONS.items())
        response = self.llm.complete(
            LLMRequest(
                system=CODER_SYSTEM % listing,
                messages=[user(coding_record(traj))],
                purpose="code_behaviour",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        )
        try:
            parsed = extract_json_object(response.text)
        except ValueError:
            parsed = {}
        codes: dict[str, Any] = {}
        for name in BEHAVIOUR_DEFINITIONS:
            entry = parsed.get(name) if isinstance(parsed.get(name), dict) else {}
            present = entry.get("present")
            codes[name] = {
                "present": present if isinstance(present, bool) else None,
                "step": entry.get("step"),
                "evidence": str(entry.get("evidence", ""))[:300],
            }
        return {"codes": codes, "coder": self.llm.model, "llm_call_id": response.call_id}


def cohen_kappa(a: list[bool], b: list[bool]) -> float | None:
    """Agreement between two coders beyond chance, for one yes/no behaviour."""
    pairs = [(x, y) for x, y in zip(a, b, strict=True) if x is not None and y is not None]
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(1 for x, y in pairs if x == y) / n
    pa = sum(1 for x, _ in pairs if x) / n
    pb = sum(1 for _, y in pairs if y) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected >= 1.0:
        return 1.0 if observed == 1.0 else None
    return (observed - expected) / (1 - expected)
