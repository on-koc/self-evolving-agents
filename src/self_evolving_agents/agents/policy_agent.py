"""Agents that execute a rule policy, with or without a language model writing it."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from ..envs.base import TextEnv
from ..llm import BudgetExceeded, LLMError, LLMRequest, assistant, user
from ..methods.reasoningbank import prompts
from ..methods.reasoningbank.render import render_memory
from ..methods.reasoningbank.schema import MemoryItem
from ..policies import PolicyError, RulePolicy, always
from ..types import Action, Observation, Step, Trajectory
from .base import Agent, run_episode


class PolicyAgent(Agent):
    """Runs a fixed :class:`RulePolicy`. No language model is involved."""

    def __init__(self, policy: RulePolicy):
        self.policy = policy

    @property
    def descriptor(self) -> dict[str, Any]:
        return {
            "id": f"policy:{self.policy.fingerprint}",
            "type": "rule-policy",
            "policy": self.policy.to_dict(),
        }

    def run(
        self,
        env: TextEnv,
        *,
        first_observation: Observation | None = None,
        memory: Sequence[MemoryItem] = (),
        notes: str = "",
        sample: int = 0,
        meta: dict[str, Any] | None = None,
    ) -> Trajectory:
        policy = self.policy

        def decide(observation: Observation, steps: list[Step]):
            name, rule = policy.explain(observation.features)
            return "", Action(name), None, {"rule": rule}

        return run_episode(
            env,
            decide,
            agent=self.descriptor,
            first_observation=first_observation,
            memory=memory,
            meta={"policy_text": policy.describe(), **(meta or {})},
        )


_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any]:
    """Pull the last JSON object out of a model reply (fenced block preferred)."""
    candidates = _JSON_BLOCK.findall(text)
    if not candidates:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("no JSON object found in the reply")
        candidates = [text[start : end + 1]]
    try:
        data = json.loads(candidates[-1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"the JSON is not valid ({exc.msg} at position {exc.pos})") from None
    if not isinstance(data, dict):
        raise ValueError("the JSON must be an object")
    return data


class PolicyProgramAgent(Agent):
    """Asks the model for one rule policy per episode and then executes it.

    This is the cheap way to put a language model in charge of a long simulation:
    one call instead of one per step. It also makes the strategy explicit, so the
    memory extractor sees exactly which rule produced which behaviour, and the same
    strategy can be rerun on other seeds.

    If the model cannot produce a valid policy within ``max_attempts`` replies, the
    episode runs the environment's fallback action throughout and is flagged with
    ``meta["policy_error"]``.
    """

    def __init__(self, llm: Any, *, max_attempts: int = 3, max_tokens: int = 16000):
        self.llm = llm
        self.max_attempts = max_attempts
        self.max_tokens = max_tokens

    @property
    def descriptor(self) -> dict[str, Any]:
        return {
            "id": f"policy-program:{self.llm.model}",
            "type": "policy-program",
            "model": self.llm.model,
        }

    def system_prompt(self, env: TextEnv, memory: Sequence[MemoryItem], notes: str) -> str:
        spec = env.spec
        features = "\n".join(f"- `{name}`: {doc}" for name, doc in spec.feature_docs.items())
        parts = [
            spec.instructions(),
            "## Task\n" + env.query,
            "## Features available to the policy\n" + features,
            "## Actions available to the policy\n" + ", ".join(f"`{a}`" for a in spec.action_names),
            "## Your job\n" + prompts.POLICY_FORMAT,
        ]
        if memory:
            parts.append(prompts.MEMORY_INSTRUCTION_POLICY + "\n\n" + render_memory(memory))
        if notes:
            parts.append(prompts.REFINEMENT_NOTES_HEADER + "\n" + notes)
        return "\n\n".join(parts)

    def write_policy(
        self, env: TextEnv, memory: Sequence[MemoryItem], notes: str, sample: int
    ) -> tuple[RulePolicy, dict[str, Any]]:
        """Obtain a validated policy from the model. Returns ``(policy, info)``."""
        spec = env.spec
        if not spec.feature_docs or not spec.action_names:
            raise PolicyError(f"{env.env_id} exposes no features for rule policies")
        system = self.system_prompt(env, memory, notes)
        messages = [user("Write the policy for this task now.")]
        info: dict[str, Any] = {"policy_attempts": 0, "policy_call_ids": []}
        error = "no reply"
        for _ in range(self.max_attempts):
            info["policy_attempts"] += 1
            try:
                response = self.llm.complete(
                    LLMRequest(
                        system=system,
                        messages=messages,
                        purpose="policy",
                        max_tokens=self.max_tokens,
                        sample=sample,
                    )
                )
            except BudgetExceeded:
                raise
            except LLMError as exc:
                error = f"model call failed: {exc}"
                break
            if response.call_id:
                info["policy_call_ids"].append(response.call_id)
            try:
                data = extract_json_object(response.text)
                policy = RulePolicy.from_dict(data)
                policy.validate(spec.feature_names, spec.action_names)
            except (ValueError, PolicyError) as exc:
                error = str(exc)
                messages = messages + [
                    assistant(response.text),
                    user(
                        f"That policy cannot be used: {error}. Reply again with a corrected policy."
                    ),
                ]
                continue
            json_start = response.text.find("```")
            info["policy_rationale"] = response.text[
                : json_start if json_start > 0 else 600
            ].strip()
            return policy, info
        info["policy_error"] = error
        fallback = always(env.fallback_action().name, name="fallback")
        return fallback, info

    def run(
        self,
        env: TextEnv,
        *,
        first_observation: Observation | None = None,
        memory: Sequence[MemoryItem] = (),
        notes: str = "",
        sample: int = 0,
        meta: dict[str, Any] | None = None,
    ) -> Trajectory:
        first = first_observation if first_observation is not None else env.reset()
        policy, info = self.write_policy(env, memory, notes, sample)

        def decide(observation: Observation, steps: list[Step]):
            name, rule = policy.explain(observation.features)
            return "", Action(name), None, {"rule": rule}

        return run_episode(
            env,
            decide,
            agent=self.descriptor,
            first_observation=first,
            memory=memory,
            meta={
                "policy": policy.to_dict(),
                "policy_text": policy.describe(),
                "sample": sample,
                **info,
                **(meta or {}),
            },
        )
