"""The step-by-step language-model agent (ReAct style), as used in the ReasoningBank paper.

At every step the model sees the task, whatever the memory method put in the system
prompt, a window of recent steps and the current observation, and replies with
``<think>...</think><action>...</action>``.
"""

from __future__ import annotations

import re
from typing import Any

from ..envs.base import ActionParseError, TextEnv
from ..llm import BudgetExceeded, LLMError, LLMRequest, assistant, user
from ..types import Action, Observation, Step, Trajectory
from .base import Agent, MemoryBlock, run_episode

_THINK = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
_ACTION = re.compile(r"<action>(.*?)</action>", re.DOTALL | re.IGNORECASE)

RESPONSE_FORMAT = (
    "At every step, reply with brief reasoning followed by exactly one action, in this format:\n"
    "<think>your reasoning in a few sentences</think>\n"
    "<action>{action_format}</action>"
)


def parse_reply(text: str, env: TextEnv) -> tuple[str, Action]:
    """Split a model reply into its reasoning and a validated action.

    If the reply has several ``<action>`` blocks the last one is taken as the final
    decision. A reply with no ``<action>`` block is still accepted when the text
    outside the reasoning parses as an action on its own.
    """
    thoughts = [t.strip() for t in _THINK.findall(text)]
    actions = _ACTION.findall(text)
    if actions:
        candidate = actions[-1]
    else:
        candidate = _THINK.sub("", text)
        open_think = candidate.lower().rfind("<think>")
        if open_think != -1:  # reasoning was cut off before it closed
            raise ActionParseError("the reply has no <action>...</action> block")
    if not candidate.strip():
        raise ActionParseError("the reply has no <action>...</action> block")
    action = env.parse_action(candidate)
    thought = " ".join(thoughts)
    if not thought:
        cut = text.lower().find("<action>")
        thought = (text[:cut] if cut > 0 else "").strip()
    return thought, action


class StepwiseAgent(Agent):
    """One model call per decision.

    Args:
        llm: anything with ``complete(LLMRequest)`` and a ``model`` attribute.
        history_window: how many recent steps are shown as one-line summaries.
        thought_window: for how many of those the agent's own reasoning is repeated.
        parse_retries: how often to ask again when a reply cannot be parsed. After
            that the environment's fallback action is taken and the step is flagged.
        temperature: decoding temperature requested for every action (0.7 in the
            paper). Backends whose models do not accept one ignore it.
    """

    def __init__(
        self,
        llm: Any,
        *,
        history_window: int = 10,
        thought_window: int = 3,
        parse_retries: int = 1,
        max_tokens: int = 16000,
        temperature: float | None = 0.7,
    ):
        self.llm = llm
        self.history_window = history_window
        self.thought_window = thought_window
        self.parse_retries = parse_retries
        self.max_tokens = max_tokens
        self.temperature = temperature

    @property
    def descriptor(self) -> dict[str, Any]:
        return {
            "id": f"stepwise:{self.llm.model}",
            "type": "stepwise",
            "model": self.llm.model,
            "history_window": self.history_window,
            "thought_window": self.thought_window,
            "temperature": self.temperature,
        }

    # ------------------------------------------------------------------ prompts

    def system_prompt(self, env: TextEnv, memory: MemoryBlock | None, notes: str) -> str:
        """Everything that stays fixed for the episode. Identical at every step, so it can be cached.

        Memory goes at the end of the system prompt, as in the paper ("retrieved items
        are injected into the agent's system instruction").
        """
        spec = env.spec
        parts = [
            spec.instructions(),
            "## Task\n" + env.query,
            "## Response format\n" + RESPONSE_FORMAT.format(action_format=spec.action_format),
        ]
        if memory:
            parts.append(memory.text.strip())
        if notes:
            parts.append(notes.strip())
        return "\n\n".join(parts)

    def step_prompt(self, observation: Observation, steps: list[Step]) -> str:
        parts = []
        if steps:
            recent = steps[-self.history_window :] if self.history_window > 0 else []
            earlier = len(steps) - len(recent)
            lines = []
            if earlier > 0:
                lines.append(f"({earlier} earlier steps not shown)")
            for step in recent:
                line = f"step {step.index + 1}: {step.brief} | action: {step.action}"
                if step.result:
                    line += f" | {step.result}"
                if step.thought and step.index >= len(steps) - self.thought_window:
                    thought = " ".join(step.thought.split())
                    line += f"\n    your reasoning then: {thought[:300]}"
                lines.append(line)
            total = sum(s.reward for s in steps)
            parts.append(
                "## Recent steps (oldest first)\n"
                + "\n".join(lines)
                + f"\nTotal reward so far: {total:+.4f} after {len(steps)} steps."
            )
        parts.append("## Current observation\n" + observation.text)
        parts.append("Choose the next action.")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------ acting

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
        first = first_observation if first_observation is not None else env.reset()
        system = self.system_prompt(env, memory, notes)

        def decide(observation: Observation, steps: list[Step]):
            messages = [user(self.step_prompt(observation, steps))]
            diagnostics: dict[str, Any] = {}
            call_id: str | None = None
            for attempt in range(self.parse_retries + 1):
                try:
                    response = self.llm.complete(
                        LLMRequest(
                            system=system,
                            messages=messages,
                            purpose="act",
                            max_tokens=self.max_tokens,
                            temperature=self.temperature,
                            sample=sample,
                            meta={"task": env.task.key, "step": len(steps), "attempt": attempt},
                        )
                    )
                except BudgetExceeded:
                    raise  # a spent budget has to stop the run, not be papered over
                except LLMError as exc:
                    # A refusal or a failed call must not sink the whole episode.
                    diagnostics["llm_error"] = str(exc)[:200]
                    return (
                        "(no usable reply from the model)",
                        env.fallback_action(),
                        call_id,
                        diagnostics,
                    )
                call_id = response.call_id or None
                try:
                    thought, action = parse_reply(response.text, env)
                except ActionParseError as exc:
                    diagnostics["parse_error"] = str(exc)[:200]
                    messages = messages + [
                        assistant(response.text or "(empty reply)"),
                        user(
                            f"Your reply could not be used: {exc}. Reply again in the required "
                            "format with exactly one action."
                        ),
                    ]
                    continue
                diagnostics["parse_attempts"] = attempt + 1
                return thought, action, call_id, diagnostics
            diagnostics["fallback"] = True
            return "(reply could not be parsed)", env.fallback_action(), call_id, diagnostics

        return run_episode(
            env,
            decide,
            agent=self.descriptor,
            first_observation=first,
            memory_item_ids=memory.item_ids if memory else (),
            meta={"sample": sample, **(meta or {})},
        )
