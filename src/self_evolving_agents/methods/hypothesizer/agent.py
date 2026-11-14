"""DiscoveryWorld's Hypothesizer agent, ported to this repository's agent interface.

Each step has two model calls, as in ``GPT4HypothesizerOneStep``:

1. **act**: the observation (the API's JSON), the actions, the last three actions
   with their explanations, the current scientific knowledge; the reply is a JSON
   action with an ``explanation``, a ``memory`` note and ``running_hypotheses``.
2. **knowledge**: the same context; the reply adds measurements and hypotheses (with a
   status: pending, confirmed, rejected) to the knowledge store.

Every ten steps a third call consolidates the store (at most 40 entries and 2000
tokens). The store starts empty in every episode: the Hypothesizer remembers within
an episode, not across episodes. Across-episode memory, when a method provides it,
is placed in the action prompt (see :mod:`.prompts`).

What differs from the released agent is listed in ``docs/methods/hypothesizer.md``.
"""

from __future__ import annotations

import copy
import json
import time
from functools import lru_cache
from typing import Any

from ...agents.base import Agent, MemoryBlock, run_episode
from ...envs.base import TextEnv
from ...llm import LLMRequest, user
from ...types import Action, Observation, Step, Trajectory
from . import prompts

ERROR_ACTION = (
    "ERROR: Could not parse the last action that was generated.  Please be careful in "
    "generating valid JSON."
)


def extract_json(text: str) -> Any:
    """``extractJSONfromGPT4Response``: the first code block, else the whole reply."""
    lines = text.split("\n")
    start = 0
    for idx, line in enumerate(lines):
        if line.startswith("```json") or line.startswith("```"):
            start = idx + 1
            break
    end = 0
    for idx, line in enumerate(lines):
        if idx > start and line.startswith("```"):
            end = idx
            break
    candidate = "\n".join(lines[start:end]) if end > 0 else text
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None


@lru_cache(maxsize=1)
def _encoding() -> Any:
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # noqa: BLE001 - its data file is downloaded on first use and may be unreachable
        return None


def count_tokens(text: str) -> tuple[int, str]:
    """Tokens as the original counts them (``cl100k_base``), or an estimate without tiktoken."""
    encoding = _encoding()
    if encoding is not None:
        return len(encoding.encode(text)), "tiktoken-cl100k_base"
    return max(1, len(text) // 4), "chars/4"


def interactable(observation: dict[str, Any]) -> str:
    """``mkShortInteractableObjectList``."""
    ui = observation["ui"]
    parts = [
        '{"name": "' + obj["name"] + '", "uuid": ' + str(obj["uuid"]) + "}"
        for obj in list(ui["inventoryObjects"]) + list(ui["accessibleEnvironmentObjects"])
    ]
    return "[" + ", ".join(parts) + "]"


def visible_object(uuid: Any, observation: dict[str, Any]) -> dict[str, Any] | None:
    """``getVisibleObjectByUUID``: inventory and accessible objects only."""
    ui = observation["ui"]
    for obj in list(ui["inventoryObjects"]) + list(ui["accessibleEnvironmentObjects"]):
        if obj["uuid"] == uuid:
            return obj
    return None


class HypothesizerAgent(Agent):
    """The act-then-reflect agent of DiscoveryWorld, with an optional cross-episode memory.

    Args:
        llm: the model, for every call.
        observation: ``"json"`` shows the API's observation as the original does (about
            4,000 tokens); ``"text"`` shows the compact rendering of this repository's
            environment instead, for models with a small context. Not in the original.
        temperature: 0.1 for every call, as in the original.
        act_max_tokens, knowledge_max_tokens: reply limits of the two calls (800, 3000).
        consolidate_every: steps between consolidations (10).
        kb_max_entries, kb_max_tokens: the limits stated in the consolidation prompt.
        fixed_dialog_prompt: show the dialog in the dialog addition (the original's
            evidently intended text); off by default, as released.
    """

    def __init__(
        self,
        llm: Any,
        *,
        observation: str = "json",
        temperature: float = 0.1,
        act_max_tokens: int = 800,
        knowledge_max_tokens: int = 3000,
        consolidate_every: int = 10,
        kb_max_entries: int = 40,
        kb_max_tokens: int = 2000,
        fixed_dialog_prompt: bool = False,
    ):
        if observation not in ("json", "text"):
            raise ValueError("observation must be 'json' or 'text'")
        self.llm = llm
        self.observation = observation
        self.temperature = temperature
        self.act_max_tokens = act_max_tokens
        self.knowledge_max_tokens = knowledge_max_tokens
        self.consolidate_every = consolidate_every
        self.kb_max_entries = kb_max_entries
        self.kb_max_tokens = kb_max_tokens
        self.fixed_dialog_prompt = fixed_dialog_prompt

    @property
    def descriptor(self) -> dict[str, Any]:
        return {
            "id": f"hypothesizer:{getattr(self.llm, 'model', 'model')}",
            "kind": "hypothesizer",
            "model": getattr(self.llm, "model", None),
            "observation": self.observation,
            "temperature": self.temperature,
            "consolidate_every": self.consolidate_every,
            "fixed_dialog_prompt": self.fixed_dialog_prompt,
        }

    # ------------------------------------------------------------------ calls

    def _ask(self, prompt: str, purpose: str, max_tokens: int, sample: int, step: int) -> Any:
        return self.llm.complete(
            LLMRequest(
                system="",
                messages=[user(prompt)],
                purpose=purpose,
                max_tokens=max_tokens,
                temperature=self.temperature,
                sample=sample,
                meta={"step": step},
            )
        )

    # ------------------------------------------------------------------ episode

    def run(
        self,
        env: TextEnv,
        *,
        first_observation: Observation | None = None,
        memory: MemoryBlock | None = None,
        notes: str = "",
        sample: int = 0,
        meta: dict[str, Any] | None = None,
    ) -> Trajectory:
        for needed in ("api_observation", "known_actions", "action_help", "teleport_locations"):
            if not hasattr(env, needed):
                raise TypeError("the Hypothesizer agent needs the DiscoveryWorld environment")
        memory = memory or MemoryBlock()
        memory_text = "\n\n".join(part for part in (memory.text.strip(), notes.strip()) if part)
        history: list[dict[str, Any]] = [
            {
                "action": "This is the first action",
                "explanation": "This is the first explanation",
                "memory": "This is the first memory",
                "running_hypotheses": [],
            }
        ]
        knowledge: dict[str, Any] = {"scientific_knowledge": []}
        consolidations: list[dict[str, Any]] = []
        counter = {"name": ""}
        started = time.time()

        def decide(
            observation: Observation, steps: list[Step]
        ) -> tuple[str, Action, str | None, dict[str, Any]]:
            index = len(steps)
            api_obs = copy.deepcopy(env.api_observation())  # type: ignore[attr-defined]
            ui = api_obs["ui"]
            if steps:
                previous = steps[-1]
                if not previous.info.get("parse_failure"):
                    history[-1]["errors"] = list(previous.info.get("errors") or [])
            history[-1]["result_of_last_action"] = ui["lastActionMessage"]
            history[-1]["extended_action_message"] = ui["extended_action_message"]

            shown = api_obs if self.observation == "json" else {"observation": observation.text}
            head = prompts.action_prompt_head(
                shown,
                env.known_actions(),  # type: ignore[attr-defined]
                env.action_help(),  # type: ignore[attr-defined]
                history,
                env.teleport_locations(),  # type: ignore[attr-defined]
                ui["agentLocation"]["faceDirection"],
                ui["agentLocation"]["directions_you_can_move"],
            )
            tail = prompts.action_prompt_tail(knowledge, interactable(api_obs), memory_text)
            dialog = ""
            if env.in_dialog():  # type: ignore[attr-defined]
                dialog = prompts.dialog_text(ui["dialog_box"], fixed=self.fixed_dialog_prompt)
            prompt = head + tail + dialog + prompts.DEBUG_TEXT

            reply = self._ask(prompt, "act", self.act_max_tokens, sample, index)
            parsed = extract_json(reply.text)
            diagnostics: dict[str, Any] = {"parse_failure": False}

            if not isinstance(parsed, dict):
                last_memory, last_hypotheses = _carried(history, take_last_directly=True)
                entry = {
                    "action": ERROR_ACTION,
                    "explanation": "",
                    "memory": last_memory,
                    "running_hypotheses": last_hypotheses,
                    "step": len(history),
                }
                action = Action("NOOP", {"reason": "the reply was not valid JSON"})
                diagnostics.update(parse_failure=True, parse_error="the reply was not valid JSON")
            else:
                entry = dict(parsed)
                entry["step"] = len(history)
                if "memory" not in entry:
                    entry["memory"] = _carried(history)[0]
                if "running_hypotheses" not in entry:
                    entry["running_hypotheses"] = _carried(history)[1]
                for key in ("arg1", "arg2"):
                    if entry.get(key) is not None:
                        obj = visible_object(entry[key], api_obs)
                        if obj is not None:
                            entry[f"{key}_desc"] = obj["name"] + ": " + obj["description"]
                try:
                    action = env.parse_action(json.dumps(parsed))
                except Exception as exc:  # noqa: BLE001 - an action the game rejects
                    # The original passes such a reply to the game, which refuses it; the
                    # world advances either way.
                    action = Action("NOOP", {"reason": f"invalid action: {exc}"})
                    diagnostics["parse_error"] = str(exc)
            history.append(entry)

            # Knowledge step. As in the original, its prompt is the context of this
            # step's decision, so the result of the action is seen at the next step.
            learned = self._ask(
                prompts.knowledge_prompt(head, knowledge),
                "knowledge",
                self.knowledge_max_tokens,
                sample,
                index,
            )
            added = extract_json(learned.text)
            new_items: list[Any] = []
            if isinstance(added, dict) and isinstance(added.get("scientific_knowledge"), list):
                new_items = [
                    item for item in added["scientific_knowledge"] if isinstance(item, dict)
                ]
                for item in new_items:
                    item["step"] = ui["world_steps"]
                knowledge["scientific_knowledge"].extend(new_items)

            if index % self.consolidate_every == 0 and index > 0:
                consolidations.append(self._consolidate(knowledge, index, sample, counter))

            diagnostics.update(
                explanation=str(entry.get("explanation", "")),
                memory=entry.get("memory"),
                running_hypotheses=entry.get("running_hypotheses"),
                knowledge_added=new_items,
                knowledge_call_id=learned.call_id,
            )
            thought = str(entry.get("explanation", "")) if isinstance(parsed, dict) else ""
            return thought, action, reply.call_id, diagnostics

        traj = run_episode(
            env,
            decide,
            agent=self.descriptor,
            first_observation=first_observation,
            memory_item_ids=memory.item_ids,
            meta=meta,
        )
        traj.meta["scientific_knowledge"] = knowledge["scientific_knowledge"]
        traj.meta["knowledge_text"] = json.dumps(knowledge, indent=4, sort_keys=True)
        traj.meta["consolidations"] = consolidations
        traj.meta["token_counter"] = counter["name"] or "not needed"
        traj.meta["agent_seconds"] = round(time.time() - started, 2)
        return traj

    def _consolidate(
        self, knowledge: dict[str, Any], step: int, sample: int, counter: dict[str, str]
    ) -> dict[str, Any]:
        before = len(knowledge["scientific_knowledge"])
        tokens, counter["name"] = count_tokens(json.dumps(knowledge, indent=4, sort_keys=True))
        reply = self._ask(
            prompts.consolidation_prompt(
                knowledge, tokens, self.kb_max_entries, self.kb_max_tokens
            ),
            "consolidate",
            self.knowledge_max_tokens,
            sample,
            step,
        )
        parsed = extract_json(reply.text)
        record: dict[str, Any] = {"step": step, "entries_before": before, "tokens_before": tokens}
        new = parsed.get("scientific_knowledge") if isinstance(parsed, dict) else None
        if isinstance(new, list) and new:
            knowledge["scientific_knowledge"] = new
            record["entries_after"] = len(new)
        else:
            record["error"] = "Failed to parse response -- knowledge not consolidated."
        return record


def _carried(history: list[dict[str, Any]], take_last_directly: bool = False) -> tuple[Any, Any]:
    """The most recent memory note and running hypotheses, labelled as carried over.

    After an unreadable reply the original first takes the previous step's values as
    they are, and only searches further back (with the label) for what is missing;
    after a reply that lacks a key it always searches back with the label.
    """
    last_memory = None
    last_hypotheses = None
    if take_last_directly and history:
        last_memory = history[-1].get("memory")
        last_hypotheses = history[-1].get("running_hypotheses")
    for idx in range(len(history) - 1, -1, -1):
        step = history[idx]
        if last_memory is None and "memory" in step:
            last_memory = (
                "(No last memory was found, this most recent one was taken from Step "
                + str(idx)
                + "): "
                + str(step["memory"])
            )
        if last_hypotheses is None and "running_hypotheses" in step:
            last_hypotheses = (
                "(No last running hypothesis was found, this most recent one was taken from Step "
                + str(idx)
                + "): "
                + str(step["running_hypotheses"])
            )
        if last_memory is not None and last_hypotheses is not None:
            break
    return last_memory, last_hypotheses
