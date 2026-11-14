"""An agent that executes a fixed rule policy. No language model is involved."""

from __future__ import annotations

from typing import Any

from ..envs.base import TextEnv
from ..policies import RulePolicy
from ..types import Action, Observation, Step, Trajectory
from .base import Agent, MemoryBlock, run_episode


class PolicyAgent(Agent):
    """Runs a fixed :class:`RulePolicy`. Used by every simulator-only experiment."""

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
        memory: MemoryBlock | None = None,
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
            memory_item_ids=memory.item_ids if memory else (),
            meta={"policy_text": policy.describe(), **(meta or {})},
        )
