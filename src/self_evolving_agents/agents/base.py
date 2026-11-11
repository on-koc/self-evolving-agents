"""Agent interface and the shared episode loop."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any

from ..envs.base import TextEnv
from ..reasoningbank.schema import MemoryItem
from ..types import Action, Observation, Step, Trajectory, new_id

#: ``decide(observation, steps_so_far) -> (thought, action, llm_call_id, diagnostics)``
Decide = Callable[[Observation, list[Step]], tuple[str, Action, str | None, dict[str, Any]]]


class Agent(ABC):
    """Something that can play one episode of an environment.

    ``memory`` is what was retrieved for this task, ``notes`` is free text carried
    over from earlier attempts at the same task (used by sequential test-time
    scaling), and ``sample`` distinguishes repeated attempts so that each one is a
    separate draw from the model. Pass ``first_observation`` when the environment
    has already been reset (the caller needed the task text first); otherwise the
    agent resets it.
    """

    @property
    @abstractmethod
    def descriptor(self) -> dict[str, Any]:
        """Identity of the agent for provenance; must contain a stable ``id``."""

    @abstractmethod
    def run(
        self,
        env: TextEnv,
        *,
        first_observation: Observation | None = None,
        memory: Sequence[MemoryItem] = (),
        notes: str = "",
        sample: int = 0,
        meta: dict[str, Any] | None = None,
    ) -> Trajectory: ...


def run_episode(
    env: TextEnv,
    decide: Decide,
    *,
    agent: dict[str, Any],
    first_observation: Observation | None = None,
    memory: Sequence[MemoryItem] = (),
    meta: dict[str, Any] | None = None,
    max_steps: int | None = None,
) -> Trajectory:
    """Play one episode, recording every step.

    The environment must already be reset if ``first_observation`` is given;
    otherwise it is reset here.
    """
    observation = first_observation if first_observation is not None else env.reset()
    traj = Trajectory(
        id=new_id("traj"),
        task=env.task,
        query=env.query,
        agent=dict(agent),
        memory_item_ids=[m.id for m in memory],
        meta=dict(meta or {}),
    )
    done = False
    while not done:
        thought, action, call_id, diagnostics = decide(observation, traj.steps)
        result = env.step(action)
        outcome_text = " ".join(part for part in (result.summary, result.event) if part)
        traj.steps.append(
            Step(
                index=len(traj.steps),
                observation=observation.text,
                brief=observation.brief,
                thought=thought,
                action=action.render(),
                reward=float(result.reward),
                result=outcome_text,
                features=dict(observation.features),
                info={**result.info, **diagnostics},
                llm_call_id=call_id,
            )
        )
        observation = result.observation
        done = result.done or (max_steps is not None and len(traj.steps) >= max_steps)
    traj.final_observation = observation.text
    traj.outcome = env.outcome()
    traj.finished_at = time.time()
    return traj
