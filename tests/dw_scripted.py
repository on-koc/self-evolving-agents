"""Scripted model replies for comparing DiscoveryWorld's ReAct and Plan-and-Execute
with their ports.

A reply depends only on the prompt, so two runs that send identical prompts receive
identical replies and stay in step; the first prompt that differs shows where they
part. The replies are chosen to exercise what the agents do: instruments (whose
readings are high-importance messages), talking to characters and dialogs, invalid
actions, teleporting, reading, long thoughts (so that the history is trimmed),
replies with and without code fences, and, for Plan-and-Execute, subtasks that end
in success and in failure, a subtask long enough to draw the "are you sure" warning,
and a plan that ends with "Done!".

``tests/data/discoveryworld_baseline_prompts.json`` holds fingerprints of the prompts
DiscoveryWorld's released code (ReComA) sent when given these replies.
"""

from __future__ import annotations

import json
import re
from typing import Any

SCENERY = {"floor", "wall", "grass", "path", "sand", "dirt", "road", "fence"}
LONG = (
    "I am keeping track of what I have measured so far. Task: find out what matters. "
    "The readings are noted with care and compared against each other, step by step, "
    "so that later I can tell which hypothesis survives and which one the evidence rules out."
)
DIRECTIONS = ["north", "east", "south", "west"]


def _observation(prompt: str) -> dict[str, Any]:
    m = re.search(r"Current Environment Observation:\n```json\n(.*?)\n```", prompt, re.DOTALL)
    return json.loads(m.group(1)) if m else {}


def _teleports(prompt: str) -> list[str]:
    m = re.search(r"Valid Teleport Locations:\n```json\n(.*?)\n```", prompt, re.DOTALL)
    return list(json.loads(m.group(1)).keys()) if m else []


def _wrap(action: dict[str, Any], style: int) -> str:
    text = json.dumps(action)
    if style == 0:
        return "```json\n" + text + "\n```"
    if style == 1:
        return "Here is my action.\n```json\n" + text + "\n```\nDone."
    if style == 2:
        return "  " + text
    return "```json\n" + text + "\n"


def _instruments(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        o
        for o in objects
        if any(w in o.get("name", "") for w in ("meter", "scope", "spectrometer"))
    ]


def act_reply(prompt: str) -> str:
    ui = _observation(prompt).get("ui") or {}
    step = int(ui.get("world_steps") or 0)
    history = prompt.split("History of action-observations:", 1)[-1]
    actions_here = history.count("Action:\n```json\n")
    if "Previous Sub-Tasks:" in prompt:
        sub = prompt.count("Subtask ")
        if actions_here >= (2 if sub % 2 == 0 else 7):
            verdict = "Task completed!" if sub % 2 == 0 else "Task failed!"
            thought = "subtask " + str(sub) + " " + LONG[:80]
            return _wrap({"action": "SUBMIT", "arg1": verdict, "thought": thought}, step % 4)
    elif step >= 26:
        return _wrap({"action": "SUBMIT", "arg1": "Task completed!", "thought": "done"}, 0)
    if (ui.get("dialog_box") or {}).get("is_in_dialog"):
        options = list((ui["dialog_box"].get("dialogOptions") or {}).keys())
        choice = int(options[-1]) if options else 1
        return _wrap({"chosen_dialog_option_int": choice, "thought": "talking"}, step % 4)
    inventory = [o for o in ui.get("inventoryObjects") or [] if o.get("name") not in SCENERY]
    reach = [
        o for o in ui.get("accessibleEnvironmentObjects") or [] if o.get("name") not in SCENERY
    ]
    nearby = [
        o
        for objects in ((ui.get("nearbyObjects") or {}).get("objects") or {}).values()
        for o in objects
        if o.get("name") not in SCENERY
    ]
    thought = LONG * 3 if step % 2 == 0 else "short thought at step " + str(step)
    cycle = step % 9
    characters = (ui.get("nearbyAgents") or {}).get("list_of_agents") or {}
    npcs = {int(n) for key in characters for n in re.findall(r"uuid (\d+)", key)}
    people_reach = [o for o in reach if o.get("uuid") in npcs]
    people_near = [o for o in nearby if o.get("name") == "agent"]
    reach = [o for o in reach if o.get("uuid") not in npcs]
    nearby = [o for o in nearby if o.get("name") != "agent"]
    if people_reach and cycle in (1, 2, 3, 5):
        return _wrap(
            {"action": "TALK", "arg1": people_reach[0]["uuid"], "thought": thought}, step % 4
        )
    if people_near and cycle == 0:
        action = {
            "action": "TELEPORT_TO_OBJECT",
            "arg1": people_near[0]["uuid"],
            "thought": thought,
        }
        return _wrap(action, step % 4)
    if people_near and cycle in (1, 2, 3):
        action = {"action": "ROTATE_DIRECTION", "arg1": DIRECTIONS[cycle - 1], "thought": thought}
        return _wrap(action, step % 4)
    if cycle == 4:
        action = {"action": "FLY", "arg1": 1, "thought": thought}
    elif cycle == 6:
        action = {"action": "DISCOVERY_FEED_GET_UPDATES", "thought": thought}
    elif cycle == 7 and _teleports(prompt):
        names = _teleports(prompt)
        action = {
            "action": "TELEPORT_TO_LOCATION",
            "arg1": names[step % len(names)],
            "thought": thought,
        }
    elif _instruments(inventory) and reach:
        action = {
            "action": "USE",
            "arg1": _instruments(inventory)[0]["uuid"],
            "arg2": reach[step % len(reach)]["uuid"],
            "thought": thought,
        }
    elif _instruments(reach):
        action = {"action": "PICKUP", "arg1": _instruments(reach)[0]["uuid"], "thought": thought}
    elif _instruments(nearby):
        action = {
            "action": "TELEPORT_TO_OBJECT",
            "arg1": _instruments(nearby)[0]["uuid"],
            "thought": thought,
        }
    elif reach and cycle in (1, 5):
        action = {"action": "READ", "arg1": reach[0]["uuid"], "thought": thought}
    elif nearby:
        action = {
            "action": "TELEPORT_TO_OBJECT",
            "arg1": nearby[step % len(nearby)]["uuid"],
            "thought": thought,
        }
    else:
        action = {"action": "ROTATE_DIRECTION", "arg1": DIRECTIONS[step % 4], "thought": thought}
    return _wrap(action, step % 4)


def plan_reply(messages: list[dict[str, str]]) -> str:
    start = max(
        (i for i, m in enumerate(messages) if "Now solve this task" in m["content"]), default=0
    )
    done = sum(1 for m in messages[start + 1 :] if m["role"] == "assistant")
    if done >= 4:
        return " Step " + str(done + 1) + ": Done!\nthis line is cut"
    return " Step " + str(done + 1) + ": Use an instrument on the nearest object\nignored"


def reply(messages: list[dict[str, str]], max_tokens: int) -> str:
    """The scripted reply: the planner's calls have a 100-token limit, actions 400."""
    if max_tokens == 100:
        return plan_reply(messages)
    return act_reply(messages[0]["content"])


def fingerprint(messages: list[dict[str, str]]) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
