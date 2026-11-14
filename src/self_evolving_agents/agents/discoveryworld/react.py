"""DiscoveryWorld's ReAct baseline, ported to this repository's agent interface.

At every step the model sees the task, the history of its earlier actions with what
the game answered (newest first within 10,000 characters), the current observation as
the API's JSON, the actions and the objects within reach, and replies with one JSON
action carrying a ``thought``. ``SUBMIT`` ends the episode. Decoding is greedy
(temperature 0) with at most 400 reply tokens, stopped at a closing code fence, as in
``agents/recoma/configs/react.jsonnet``.

The prompt is byte-identical to the released agent's (a test compares fingerprints of
prompts produced by the original code). Where the port departs from the original, and
how memory from a method is placed in the prompt, is documented in ``docs/agents.md``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from ...envs.base import TextEnv
from ...types import Action, Observation, Step, Trajectory
from ..base import Agent, MemoryBlock, run_episode
from . import prompts, recoma

MEMORY_SLOT = "\x00memory\x00"
#: Where a method's memory goes in the action prompt: just before the task.
TASK_ANCHOR = "\n\nTask: {{ input_str }}"
UNUSABLE_REPLY = "Could not find a JSON action in the reply."


def with_memory(template: str, anchor: str) -> str:
    """The template with a slot for memory text before ``anchor``."""
    if anchor not in template:  # pragma: no cover - the templates are fixed
        raise ValueError("anchor not found in the template")
    return template.replace(anchor, "\n\n" + MEMORY_SLOT + anchor, 1)


def fill(template: str, values: dict[str, Any], memory_text: str) -> str:
    """Render a template; memory text, if any, replaces the slot (else the slot vanishes)."""
    if not memory_text:
        return prompts.render(template, values)
    return prompts.render(with_memory(template, TASK_ANCHOR), values).replace(
        MEMORY_SLOT, memory_text, 1
    )


def required_env(env: TextEnv) -> None:
    for needed in (
        "api_observation",
        "refresh_observation",
        "known_actions",
        "action_help",
        "teleport_locations",
        "in_dialog",
        "last_action_result",
    ):
        if not hasattr(env, needed):
            raise TypeError("this agent needs the DiscoveryWorld environment")


def to_action(action_json: dict[str, Any]) -> Action:
    """The model's JSON as an action that is sent to the game unchanged."""
    if "action" not in action_json and "chosen_dialog_option_int" in action_json:
        return Action(
            "DIALOG",
            {"chosen_dialog_option_int": action_json["chosen_dialog_option_int"]},
            payload=action_json,
        )
    args = {k: action_json[k] for k in ("arg1", "arg2") if action_json.get(k) is not None}
    return Action(str(action_json.get("action")), args, payload=action_json)


@dataclass
class Decision:
    """What one action call of a ReAct controller produced."""

    reply: str
    call_id: str | None
    action_json: dict[str, Any] | None
    usable: bool
    submitted: bool = False
    output: str = ""

    @property
    def thought(self) -> str:
        if not isinstance(self.action_json, dict):
            return ""
        thought = self.action_json.get("thought", "")
        return thought if isinstance(thought, str) else json.dumps(thought)


@dataclass
class Reads:
    """Keeps the agent's observation reads in step with the original's.

    The original reads the observation once for every model call (planner calls
    included). Right after an action the environment has just read it, and that read
    stands for the original's, so the next call uses it; any other call reads afresh.
    With ``released=False`` the agent never reads beyond what the environment does.
    """

    released: bool = True
    fresh: bool = False

    def observation(self, env: Any) -> dict[str, Any]:
        if not self.released or self.fresh:
            self.fresh = False
            return env.api_observation()
        return env.refresh_observation()

    def after_step(self) -> None:
        self.fresh = True


@dataclass
class Controller:
    """``DiscoveryWorldReactController`` with its action model, for one task or subtask."""

    llm: Any
    template: str
    temperature: float | None
    max_tokens: int
    max_output_length: int
    max_history: int = -1
    termination_suggestion: float = -1
    history: recoma.ReactHistory = field(default_factory=recoma.ReactHistory)

    def act(
        self,
        env: Any,
        reads: Reads,
        input_str: str,
        *,
        memory_text: str,
        sample: int,
        step: int,
        purpose: str = "act",
    ) -> Decision:
        prompt_input = recoma.react_input(
            input_str,
            self.history,
            max_output_length=self.max_output_length,
            max_history=self.max_history,
            termination_suggestion=self.termination_suggestion,
        )
        values = recoma.template_values(env, reads.observation(env), prompt_input)
        prompt = fill(self.template, values, memory_text)
        reply, call_id = recoma.generate(
            self.llm,
            prompt,
            max_tokens=self.max_tokens,
            stop=["```\n"],
            temperature=self.temperature,
            purpose=purpose,
            sample=sample,
            meta={"step": step},
        )
        code, kept = recoma.extract_json_output(reply)
        parsed: Any = None
        if code is not None:
            try:
                parsed = json.loads(code)
            except json.JSONDecodeError:
                parsed = None
        if not isinstance(parsed, dict):
            # The original stops the whole run here (it cannot decode the reply). The
            # port records the reply and lets a step pass without an action.
            self.history.add_action(kept, None)
            self.history.add_observation(json.dumps({"errors": [UNUSABLE_REPLY], "success": False}))
            return Decision(reply, call_id, None, usable=False)
        self.history.add_action(kept, parsed)
        if parsed.get("action") == "SUBMIT":
            output = str(parsed.get("arg1", "")) + Decision(reply, None, parsed, True).thought
            return Decision(reply, call_id, parsed, usable=True, submitted=True, output=output)
        return Decision(reply, call_id, parsed, usable=True)

    def observe(self, env: Any) -> None:
        """Add what the game answered to the last action (the original's observation)."""
        self.history.add_observation(json.dumps(env.last_action_result()))


def at_step_limit(env: Any) -> bool:
    """``max_env_calls`` of the released runner: DiscoveryWorld's counter reached the limit.

    The counter is 1 right after loading, so the runner allows one action fewer than
    the limit.
    """
    world_steps = env.api_observation()["ui"].get("world_steps")
    limit = getattr(env, "params", {}).get("max_steps")
    return world_steps is not None and limit is not None and int(world_steps) >= int(limit)


def knowledge_text(thoughts: list[str]) -> str:
    """What DiscoveryWorld's knowledge scorer grades for ReAct: every thought, numbered.

    As ``scripts/analysisReactKnowledge.py`` builds it from the run log, which holds
    the actions sent to the game (a ``SUBMIT`` never reaches it).
    """
    return "".join(f"Thought {i + 1}: {t}\n" for i, t in enumerate(thoughts))


class ReActAgent(Agent):
    """DiscoveryWorld's ReAct agent, with an optional memory from a method.

    Args:
        llm: the model.
        temperature: 0.0 (greedy), as released.
        max_tokens: reply limit of an action call (400).
        max_output_length: characters of task and history in the prompt (10,000).
        max_history: history entries kept before trimming by length; -1 keeps all
            that fit, as released.
        max_llm_calls: the episode ends once this many calls have been made (1,000 in
            the released configuration).
        released_reads: read the observation as often as the released runs did,
            including the read their logging makes after every action (on by default;
            it decides which queued messages the agent sees).
        released_step_limit: stop when DiscoveryWorld's own step counter reaches the
            step limit, as the released runner does. The counter starts at 1 when the
            world is loaded, so this allows one action fewer than the limit (99 of
            100); off, the agent may use the whole limit.
    """

    kind = "react"

    def __init__(
        self,
        llm: Any,
        *,
        temperature: float | None = 0.0,
        max_tokens: int = 400,
        max_output_length: int = 10000,
        max_history: int = -1,
        max_llm_calls: int = 1000,
        released_reads: bool = True,
        released_step_limit: bool = True,
    ):
        self.llm = llm
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_output_length = max_output_length
        self.max_history = max_history
        self.max_llm_calls = max_llm_calls
        self.released_reads = released_reads
        self.released_step_limit = released_step_limit

    @property
    def descriptor(self) -> dict[str, Any]:
        return {
            "id": f"react:{getattr(self.llm, 'model', 'model')}",
            "kind": self.kind,
            "model": getattr(self.llm, "model", None),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_output_length": self.max_output_length,
            "max_history": self.max_history,
            "released_reads": self.released_reads,
            "released_step_limit": self.released_step_limit,
        }

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
        required_env(env)
        if first_observation is None:
            first_observation = env.reset()
        env.read_after_action = self.released_reads  # type: ignore[attr-defined]
        memory = memory or MemoryBlock()
        memory_text = "\n\n".join(p for p in (memory.text.strip(), notes.strip()) if p)
        task = recoma.task_description(env.api_observation())  # type: ignore[attr-defined]
        controller = Controller(
            self.llm,
            prompts.REACT_TEMPLATE,
            self.temperature,
            self.max_tokens,
            self.max_output_length,
            self.max_history,
        )
        reads = Reads(released=self.released_reads)
        thoughts: list[str] = []
        calls = {"n": 0}
        started = time.time()

        def decide(
            observation: Observation, steps: list[Step]
        ) -> tuple[str, Action, str | None, dict[str, Any]]:
            if steps and steps[-1].info.get("sent_to_game"):
                controller.observe(env)
            if self.released_step_limit and at_step_limit(env):
                return "", Action("SUBMIT", {"arg1": "", "reason": "env_call_limit"}), None, {}
            if calls["n"] >= self.max_llm_calls:
                return "", Action("SUBMIT", {"arg1": "", "reason": "llm_call_limit"}), None, {}
            decision = controller.act(
                env, reads, task, memory_text=memory_text, sample=sample, step=len(steps)
            )
            calls["n"] += 1
            diagnostics: dict[str, Any] = {"sent_to_game": False}
            if not decision.usable:
                diagnostics.update(parse_failure=True, parse_error=UNUSABLE_REPLY)
                reads.after_step()
                return "", Action("NOOP", {"reason": UNUSABLE_REPLY}), decision.call_id, diagnostics
            if decision.submitted:
                diagnostics["submitted"] = decision.output
                return (
                    decision.thought,
                    Action("SUBMIT", {"arg1": str(decision.action_json.get("arg1", ""))}),
                    decision.call_id,
                    diagnostics,
                )
            if calls["n"] >= self.max_llm_calls:
                # The original's call limit is checked before the action is carried out.
                return (
                    decision.thought,
                    Action("SUBMIT", {"arg1": "", "reason": "llm_call_limit"}),
                    decision.call_id,
                    diagnostics,
                )
            assert decision.action_json is not None
            if "thought" in decision.action_json:
                thoughts.append(decision.thought)
            diagnostics["sent_to_game"] = True
            reads.after_step()
            return decision.thought, to_action(decision.action_json), decision.call_id, diagnostics

        traj = run_episode(
            env,
            decide,
            agent=self.descriptor,
            first_observation=first_observation,
            memory_item_ids=memory.item_ids,
            meta=meta,
        )
        traj.meta["knowledge_text"] = knowledge_text(thoughts)
        traj.meta["llm_calls"] = calls["n"]
        traj.meta["agent_seconds"] = round(time.time() - started, 2)
        return traj
