"""An agent that has the model write one rule policy per episode and then executes it."""

from __future__ import annotations

from typing import Any

from ...agents.base import Agent, MemoryBlock, run_episode
from ...envs.base import TextEnv
from ...llm import BudgetExceeded, LLMError, LLMRequest, assistant, user
from ...llm.parsing import extract_json_object
from ...policies import PolicyError, RulePolicy, always
from ...types import Action, Observation, Step, Trajectory
from . import prompts


class PolicyProgramAgent(Agent):
    """Asks the model for one rule policy per episode and then executes it.

    One model call instead of one per step. The strategy is explicit, so the memory
    extractor sees exactly which rule produced which behaviour, and the same strategy
    can be rerun on other seeds. What it cannot do is react to anything the rules do
    not anticipate.

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

    def system_prompt(self, env: TextEnv, memory: MemoryBlock | None, notes: str) -> str:
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
            parts.append(memory.text.strip())
        if notes:
            parts.append(notes.strip())
        return "\n\n".join(parts)

    def write_policy(
        self, env: TextEnv, memory: MemoryBlock | None, notes: str, sample: int
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
        memory: MemoryBlock | None = None,
        notes: str = "",
        sample: int = 0,
        meta: dict[str, Any] | None = None,
    ) -> Trajectory:
        first = first_observation if first_observation is not None else env.reset()
        policy, info = self.write_policy(env, memory, notes, sample)

        def decide(observation: Observation, steps: list[Step]):
            name, rule = policy.explain(observation.features)
            return "", Action(name), None, {"rule": rule}

        # There is no step-by-step reasoning to show an extractor, so the policy and
        # its rationale are put in front of the trajectory instead.
        header = "The agent committed to this policy before the episode:\n" + policy.describe()
        if info.get("policy_rationale"):
            header += "\n\nIts stated rationale: " + info["policy_rationale"]
        return run_episode(
            env,
            decide,
            agent=self.descriptor,
            first_observation=first,
            memory_item_ids=memory.item_ids if memory else (),
            meta={
                "policy": policy.to_dict(),
                "policy_text": policy.describe(),
                "trajectory_header": header,
                "sample": sample,
                **info,
                **(meta or {}),
            },
        )
