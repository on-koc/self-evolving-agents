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

    def _generic(self, request: LLMRequest) -> str:
        return "(offline-demo has no behaviour for this request)"
