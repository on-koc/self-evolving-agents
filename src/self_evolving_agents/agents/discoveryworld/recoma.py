"""The parts of ReComA that DiscoveryWorld's ReAct and Plan-and-Execute agents rely on.

DiscoveryWorld runs both agents on ReComA (``allenai/recoma`` at commit ``b262ab5``,
Apache License 2.0). Ported here, each function says which original it follows:

* how a prompt becomes chat messages (``LMGenerator.extract_role_messages``);
* how a reply is generated: greedy decoding, cut at the stop strings, leading
  whitespace removed (``LiteLLMGenerator.generate``);
* how the JSON action is taken from a reply, and how the history of actions and
  observations is written into the next prompt, newest first within a character
  budget (``DiscoveryWorldReactController``).

Where the original stops the whole run with an exception, the port says so and does
something that keeps the episode going; those places are listed in
``docs/agents.md``.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any

from ...llm import LLMRequest, apply_stop

_ROLE = re.compile("(USER|ASSISTANT|SYSTEM):\n", flags=re.IGNORECASE)
_FULL_CODE = r"```json\n(.*?)```"
_PARTIAL_CODE = r".*```json\n(.*)"

TRIMMED = "[TRIMMED HISTORY]\n\n"
CONTINUE_WARNING = "\n**ARE YOU SURE YOU WANT TO CONTINUE? CONSIDER SUBMITTING WITH FAILURE**\n"


def extract_role_messages(text: str) -> list[dict[str, str]]:
    """``LMGenerator.extract_role_messages``: a prompt as chat messages.

    A prompt containing ``ASSISTANT:`` on a line of its own is split at every
    ``USER:``, ``ASSISTANT:`` or ``SYSTEM:`` line (in any letter case); any other
    prompt is one user message. The original also accepts a prompt that is a JSON
    list of messages; where such a prompt does not parse, the original stops the run
    and the port falls through to the rules above.
    """
    if '"role": "user"' in text:
        try:
            messages = json.loads(text)
            if isinstance(messages, list):
                return messages
        except json.JSONDecodeError:
            pass
    if "ASSISTANT:\n" in text:
        messages: list[dict[str, Any]] = []
        last_start = 0
        for match in _ROLE.finditer(text):
            last_end = match.span()[0]
            if not messages:
                if last_end != 0:
                    raise ValueError(f"Start of the prompt has no assigned role: {text[:last_end]}")
            else:
                messages[-1]["content"] = text[last_start:last_end]
            messages.append({"role": match.group(1).lower(), "content": None})
            last_start = match.span()[1]
        messages[-1]["content"] = text[last_start:]
        return messages
    return [{"role": "user", "content": text}]


def generate(
    llm: Any,
    prompt: str,
    *,
    max_tokens: int,
    stop: list[str],
    temperature: float | None,
    purpose: str,
    sample: int,
    meta: dict[str, Any] | None = None,
) -> tuple[str, str | None]:
    """One reply as ReComA's generator returns it: cut at the stop strings, left-stripped.

    A leading ``system`` message becomes the request's system prompt; the original
    sends its prompts as user and assistant turns only, so this never happens with
    DiscoveryWorld's templates.
    """
    messages = extract_role_messages(prompt)
    system = ""
    while messages and messages[0]["role"] == "system":
        system += messages.pop(0)["content"]
    chat = [
        {"role": "user" if m["role"] == "system" else m["role"], "content": m["content"]}
        for m in messages
    ]
    reply = llm.complete(
        LLMRequest(
            system=system,
            messages=chat,
            purpose=purpose,
            max_tokens=max_tokens,
            temperature=temperature,
            sample=sample,
            meta=dict(meta or {}),
            stop=list(stop),
        )
    )
    return apply_stop(reply.text, stop).lstrip(), getattr(reply, "call_id", None) or None


def extract_json_output(output: str) -> tuple[str | None, str]:
    """``DiscoveryWorldReactController.extract_json_output`` (one JSON block is used).

    Returns ``(code, output)``: the JSON text of the action, or ``None`` if there is
    none, and the text the original keeps as the action in its history (the code
    where code was found, the reply otherwise).
    """
    for match in re.finditer(_FULL_CODE, output, flags=re.DOTALL):
        code = match.group(1).strip()
        return code, code
    code = ""
    kept = output
    partial = re.match(_PARTIAL_CODE, output, flags=re.DOTALL)
    if partial:
        code = partial.group(1).strip()
        kept = code
    if not code:
        try:
            json.loads(output)
            return output, output
        except json.JSONDecodeError:
            return None, kept
    return code, kept


@dataclass
class HistoryAction:
    action_str: str
    action_json: Any = None


@dataclass
class HistoryObservation:
    raw_observation: str


@dataclass
class ReactHistory:
    """The action-observation history of one ReAct controller (one subtask in P&E)."""

    entries: list[Any] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def add_action(self, action_str: str, action_json: Any) -> None:
        self.entries.append(HistoryAction(action_str, action_json))

    def add_observation(self, raw: str) -> None:
        self.entries.append(HistoryObservation(raw))


def build_message_thread(entries: list[Any], max_output_length: float) -> str:
    """``build_message_thread2``: the newest entries that fit, in their original order."""
    output: list[str] = []
    char_count = 0
    for message in entries[::-1]:
        if isinstance(message, HistoryAction):
            # "Small hack to make sure that "Task: " always matches the input task."
            output.append(
                "Action:\n```json\n" + message.action_str.replace("Task:", "Task :") + "\n```\n\n"
            )
        else:
            output.append("Observation:\n```json\n" + message.raw_observation + "```\n\n")
        char_count += len(output[-1])
        if char_count > max_output_length:
            output = output[:-1]
            break
    return "".join(output[::-1])


def react_input(
    input_str: str,
    history: ReactHistory,
    *,
    max_output_length: int = 10000,
    max_history: int = -1,
    termination_suggestion: float = -1,
) -> str:
    """``next_step_and_action_input``: the task and as much history as fits.

    The original repeats its trimming loop for as long as the text is too long; when
    the task text alone is longer than the limit that loop never ends. The port stops
    once no history is left.
    """
    entries = list(history.entries)
    head = input_str + "\n\nHistory of action-observations:\n"
    if max_history > 0 and len(entries) > max_history:
        entries = entries[-max_history:]
        text = head + TRIMMED
        text += build_message_thread(entries, max_output_length - len(text))
    else:
        text = head + build_message_thread(entries, max_output_length - len(head))
    while len(text) > max_output_length:
        text = head + TRIMMED
        entries = entries[1:]
        text += build_message_thread(entries, max_output_length - len(text))
        if not entries:
            break
    if termination_suggestion > 0 and len(history) > 2 * termination_suggestion:
        text += CONTINUE_WARNING
    return text


def task_description(api_observation: dict[str, Any]) -> str:
    """The task text as DiscoveryWorld's loader writes it for these agents."""
    text = ""
    for task in api_observation["ui"]["taskProgress"]:
        text += task["description"] + "\n"
    return text.strip()


def interactable_objects(api_observation: dict[str, Any]) -> str:
    """``mkShortInteractableObjectList`` of DiscoveryWorld's Hypothesizer, which these agents use."""
    ui = api_observation["ui"]
    parts = [
        '{"name": "' + obj["name"] + '", "uuid": ' + str(obj["uuid"]) + "}"
        for obj in list(ui["inventoryObjects"]) + list(ui["accessibleEnvironmentObjects"])
    ]
    return "[" + ", ".join(parts) + "]"


def template_values(env: Any, api_observation: dict[str, Any], input_str: str) -> dict[str, Any]:
    """``DiscoveryWorldPromptedLMModel.populate_template_dictionary``."""
    # A deep copy, not a JSON round trip: dialog options have integer keys, which
    # json.dumps(sort_keys=True) orders as numbers.
    observation = copy.deepcopy(api_observation)
    observation.pop("vision", None)
    observation["ui"].pop("taskProgress", None)
    location = api_observation["ui"]["agentLocation"]
    return {
        "input_str": input_str,
        "facing_direction": location["faceDirection"],
        "valid_dirs": location["directions_you_can_move"],
        "additional_instructions": env.action_help(),
        "observation": json.dumps(observation, indent=4, sort_keys=True),
        "known_actions": json.dumps(env.known_actions(), indent=4, sort_keys=True),
        "teleport_destinations": json.dumps(env.teleport_locations(), indent=4, sort_keys=True),
        "interactable_objects": interactable_objects(api_observation),
        "in_dialog": env.in_dialog(),
        "dialog_box": json.dumps(observation["ui"]["dialog_box"], indent=4, sort_keys=True),
    }
