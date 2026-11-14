"""``offline-demo``: a rule-based stand-in for a language model.

THIS IS NOT A LANGUAGE MODEL AND ITS OUTPUT IS NOT EVIDENCE OF ANYTHING.

It exists so that the complete pipeline (prompting, parsing, judging, extraction,
retrieval, test-time scaling, provenance) can be run end to end without credentials
or cost, on the scanning task family. Its "reasoning" is a handful of regular
expressions:

* acting: it scans unless a memory item in its prompt tells it otherwise. Memory
  items carry machine-readable tags such as ``(rule: charge_below=0.35)``, which it
  reads back and obeys.
* judging: "spacecraft lost" in the final state means failure.
* selecting: the attempt with the most steps (the one that flew longest) is "best".
* extracting: the failure prompt produces a canned lesson with a tag; the success
  prompt produces a canned lesson about downlinking.

So an offline run does show memory changing behaviour, but only because both ends
of that loop were written by hand to agree with each other.
"""

from __future__ import annotations

import json
import re

from .base import LLMRequest, LLMResponse, Usage

_TAG = re.compile(r"\(rule:\s*([a-z_]+)\s*=\s*([0-9.]+)\s*\)")
_PERCENT = {
    "battery": re.compile(r"Battery (\d+)%"),
    "storage": re.compile(r"data buffer (\d+)% full"),
    "wheels": re.compile(r"wheels at (\d+)% of limit"),
}


def _rules(text: str) -> dict[str, float]:
    """Read ``(rule: name=value)`` tags; for repeated names the most cautious value wins."""
    rules: dict[str, float] = {}
    for name, value in _TAG.findall(text):
        number = float(value)
        if name == "charge_below":
            rules[name] = max(rules.get(name, 0.0), number)
        elif name == "desat_above":
            rules[name] = min(rules.get(name, 1.0), number)
        else:
            rules[name] = number
    return rules


class OfflineDemoLLM:
    """Deterministic, free, and deliberately simple. See the module docstring."""

    model = "offline-demo"

    def complete(self, request: LLMRequest) -> LLMResponse:
        handler = getattr(self, f"_{request.purpose}", self._generic)
        text = handler(request)
        chars = len(request.system) + sum(len(m["content"]) for m in request.messages)
        return LLMResponse(
            text=text,
            model=self.model,
            usage=Usage(input_tokens=chars // 4, output_tokens=len(text) // 4),
        )

    # -- acting -----------------------------------------------------------------

    def _act(self, request: LLMRequest) -> str:
        if request.messages[0]["content"].startswith(_DW_ACT_START):
            return _dw_act(request.messages[0]["content"])
        observation = request.messages[0]["content"].split("## Current observation")[-1]
        if "Battery" not in observation:
            return '<think>Unfamiliar environment; taking a neutral action.</think>\n<action>{"action": "DISCOVERY_FEED_GET_UPDATES"}</action>'
        values = {}
        for key, pattern in _PERCENT.items():
            match = pattern.search(observation)
            values[key] = int(match.group(1)) / 100 if match else 0.0
        rules = _rules(request.system)
        in_view = "Ground station in view" in observation
        if values["wheels"] > rules.get("desat_above", 2.0):
            return self._reply("Wheel speed is above my remembered limit.", "desat")
        if values["battery"] < rules.get("charge_below", 0.0):
            return self._reply("Battery is below my remembered reserve.", "charge")
        if in_view and rules.get("downlink_in_view", 0.0) and values["storage"] > 0.05:
            return self._reply("A station is in view and there is data to send.", "downlink")
        return self._reply("Nothing tells me to do otherwise, so I keep collecting data.", "scan")

    @staticmethod
    def _reply(thought: str, action: str) -> str:
        return f"<think>{thought}</think>\n<action>{action}</action>"

    def _policy(self, request: LLMRequest) -> str:
        rules = _rules(request.system)
        policy = {
            "name": "offline-demo",
            "params": {
                "charge_below": rules.get("charge_below", 0.0),
                "desat_above": rules.get("desat_above", 1.0),
            },
            "rules": [
                {"if": {"wheel_speed": {">": "$desat_above"}}, "do": "desat"},
                {"if": {"battery": {"<": "$charge_below"}}, "do": "charge"},
            ],
            "default": "scan",
        }
        if rules.get("downlink_in_view"):
            policy["rules"].append(
                {"if": {"gs_in_view": {"==": 1}, "storage": {">": 0.05}}, "do": "downlink"}
            )
        return "Applying the rules I remember.\n```json\n" + json.dumps(policy, indent=2) + "\n```"

    # -- judging and selecting --------------------------------------------------

    def _judge(self, request: LLMRequest) -> str:
        text = request.messages[0]["content"]
        if "scientific discovery" in request.system:
            if "marked complete" in text or "Task status: complete" in text:
                return 'Thoughts: The task was marked complete.\nStatus: "success"'
            return 'Thoughts: The task was not marked complete.\nStatus: "failure"'
        if "spacecraft lost" in text:
            return 'Thoughts: The trajectory ends with the spacecraft lost.\nStatus: "failure"'
        return 'Thoughts: The spacecraft survived to the end of the episode.\nStatus: "success"'

    def _select(self, request: LLMRequest) -> str:
        blocks = re.split(r"^Trajectory \d+:", request.messages[0]["content"], flags=re.MULTILINE)
        lengths = [block.count("step_num:") for block in blocks[1:]]
        best = max(range(len(lengths)), key=lengths.__getitem__) + 1 if lengths else 1
        answer = {"index": [best], "analysis": "The attempt that kept flying longest."}
        return "```\n" + json.dumps(answer) + "\n```"

    # -- learning ---------------------------------------------------------------

    def _lessons(self, text: str, failed: bool = False) -> list[tuple[str, str, str]]:
        lessons = []
        wheels = "reaction wheel exceeded" in text
        if "battery was fully depleted" in text or (failed and not wheels):
            lessons.append(
                (
                    "Keep a battery reserve",
                    "Use when the battery can run flat; observed under the task's stated conditions.",
                    "Switch to charge before the battery gets low instead of scanning to the end "
                    "(rule: charge_below=0.35). Hypothesis: the reserve has to cover an eclipse.",
                )
            )
        if wheels:
            lessons.append(
                (
                    "Unload the wheels in time",
                    "Use when wheel speed climbs during the episode.",
                    "Desaturate well before the limit (rule: desat_above=0.5).",
                )
            )
        if not lessons:
            lessons.append(
                (
                    "Downlink during passes",
                    "Use when a ground station is in view and the buffer holds data.",
                    "Send data whenever a station is in view so the buffer never fills "
                    "(rule: downlink_in_view=1).",
                )
            )
        return lessons

    def _extract(self, request: LLMRequest) -> str:
        blocks = []
        # The failure prompt is the only cue when the trajectory text carries no feedback.
        failed = "attempted to resolve the task but failed" in request.system
        for i, (title, description, content) in enumerate(
            self._lessons(request.messages[0]["content"], failed), 1
        ):
            blocks.append(
                f"# Memory Item {i}\n## Title {title}\n## Description {description}\n## Content {content}"
            )
        return "\n\n".join(blocks)

    def _refine(self, request: LLMRequest) -> str:
        notes = [f"- {content}" for _, _, content in self._lessons(request.messages[0]["content"])]
        return "Notes for the next attempt:\n" + "\n".join(notes)

    # -- DiscoveryWorld --------------------------------------------------------

    def _knowledge(self, request: LLMRequest) -> str:
        """Writes down the result of the last action when it reads like a measurement."""
        results = re.findall(
            r'"result_of_last_action": "((?:[^"\\]|\\.)*)"', request.messages[0]["content"]
        )
        last = results[-1].encode().decode("unicode_escape") if results else ""
        items = []
        if any(word in last for word in ("results are as follows", "You use", "dispense")):
            items.append({"measurement": " ".join(last.split())[:300]})
        return "```json\n" + json.dumps({"scientific_knowledge": items}) + "\n```"

    def _consolidate(self, request: LLMRequest) -> str:
        text = request.messages[0]["content"]
        found = _json_after(text, "Here is the existing knowledge base:")
        items = (found or {}).get("scientific_knowledge", [])[-10:]
        return "```json\n" + json.dumps({"scientific_knowledge": items}) + "\n```"

    def _extract_investigation(self, request: LLMRequest) -> str:
        text = request.messages[0]["content"]
        evidence = [
            {"text": " ".join(line.split("| result:")[-1].split())[:200], "step": i}
            for i, line in enumerate(text.splitlines())
            if "results are as follows" in line or "dispense" in line
        ][:5]
        answer: dict[str, object] = {
            "evidence": evidence,
            "hypotheses": [
                {
                    "statement": "The task's outcome depends on which object is used.",
                    "conditions": "the world of this attempt",
                    "status": "open",
                    "supported_by": list(range(len(evidence)))[:2],
                    "contradicted_by": [],
                }
            ],
            "strategies": [
                {
                    "statement": "Pick up the instrument the task names before anything else.",
                    "applies_when": "the task names an instrument",
                    "test": "teleport to the instrument and pick it up",
                    "basis": "offline-demo canned note",
                }
            ],
        }
        labels = re.findall(r"^(S\d+): ", text, flags=re.MULTILINE)
        if labels:
            success = "attempt was a success" in text
            answer["strategy_review"] = [
                {
                    "id": label,
                    "used": True,
                    "outcome": "helped" if success else "did not help",
                    "reason": "offline-demo",
                    "revised_statement": None,
                    "revised_applies_when": None,
                }
                for label in labels
            ]
        return json.dumps(answer)

    def _grade_knowledge(self, request: LLMRequest) -> str:
        """1 if the quoted answer in the question appears in the agent's knowledge."""
        text = request.messages[0]["content"]
        found_question = re.search(r"Critical Question:\n```\n(.*?)\n```", text, flags=re.S)
        found_knowledge = re.search(r"Agent's Knowledge:\n```\n(.*?)\n```", text, flags=re.S)
        question = found_question.group(1) if found_question else ""
        knowledge = (found_knowledge.group(1) if found_knowledge else "").lower()
        quoted = re.findall(r"`([^`]+)`", question)
        hit = bool(quoted) and all(q.lower() in knowledge for q in quoted)
        return json.dumps(
            {
                "criticalQuestion": " ".join(question.split())[:200],
                "evaluation": int(hit),
                "explanation": "offline-demo: looked for the quoted answer in the knowledge",
            }
        )

    def _code_behaviour(self, request: LLMRequest) -> str:
        names = re.findall(r'^- "([a-z_]+)":', request.system, flags=re.MULTILINE)
        return json.dumps(
            {name: {"present": False, "evidence": "offline-demo codes nothing"} for name in names}
        )

    def _generic(self, request: LLMRequest) -> str:
        return "(offline-demo has no behaviour for this request)"


_DW_ACT_START = "You are playing a video game about making scientific discoveries."
_SCENERY = {"floor", "wall", "grass", "path", "sand", "dirt", "road", "fence", "agent"}


def _json_after(text: str, marker: str) -> dict | None:
    """The first ```json block after ``marker``."""
    tail = text.split(marker, 1)[-1]
    match = re.search(r"```json\n(.*?)```", tail, flags=re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _dw_act(prompt: str) -> str:
    """A rule-based explorer for DiscoveryWorld: valid actions, no intelligence."""
    observation = _json_after(prompt, "Environment Observation (as JSON):") or {}
    ui = observation.get("ui") or {}
    if (ui.get("dialog_box") or {}).get("is_in_dialog"):
        return json.dumps({"chosen_dialog_option_int": 1, "explanation": "offline-demo"})
    step = int(ui.get("world_steps") or 0)
    inventory = [o for o in ui.get("inventoryObjects") or [] if o.get("name") not in _SCENERY]
    reach = [
        o
        for o in ui.get("accessibleEnvironmentObjects") or []
        if o.get("name") not in _SCENERY
        and not str(o.get("name", "")).startswith(("table", "door"))
    ]
    nearby = [
        o
        for objects in ((ui.get("nearbyObjects") or {}).get("objects") or {}).values()
        for o in objects
        if o.get("name") not in _SCENERY
    ]
    tools = [
        o for o in inventory if any(w in o.get("name", "") for w in ("meter", "scope", "dispenser"))
    ]
    if tools and reach and step % 3 == 2:
        action = {
            "action": "USE",
            "arg1": tools[0]["uuid"],
            "arg2": reach[step % len(reach)]["uuid"],
        }
    elif reach and step % 3 == 1:
        action = {"action": "PICKUP", "arg1": reach[step % len(reach)]["uuid"]}
    elif nearby:
        action = {"action": "TELEPORT_TO_OBJECT", "arg1": nearby[step % len(nearby)]["uuid"]}
    else:
        action = {"action": "DISCOVERY_FEED_GET_UPDATES"}
    return json.dumps(
        {**action, "explanation": "offline-demo explores", "memory": "", "running_hypotheses": []}
    )
