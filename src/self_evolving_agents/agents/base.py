"""Agent interface and the shared episode loop.

Agents know nothing about any particular memory method. Whatever a method wants in
front of the agent arrives as a :class:`MemoryBlock`: text that goes into the system
prompt as it is, and the ids of the records it was built from, for provenance.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..envs.base import TextEnv
from ..types import Action, Observation, Step, Trajectory, new_id

#: ``decide(observation, steps_so_far) -> (thought, action, llm_call_id, diagnostics)``
Decide = Callable[[Observation, list[Step]], tuple[str, Action, str | None, dict[str, Any]]]


@dataclass
class MemoryBlock:
    """What a memory method puts in front of the agent for one task.

    ``text`` is appended to the agent's system prompt unchanged (instruction and
    items, already formatted by the method). ``item_ids`` names the records it was
    rendered from.
    """

    text: str = ""
    item_ids: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.text.strip())


class Agent(ABC):
    """Something that can play one episode of an environment.

    ``memory`` is what the memory method retrieved for this task, ``notes`` is further
    text for the system prompt (test-time scaling uses it to carry an agent's own
    notes from one attempt to the next), and ``sample`` distinguishes repeated
    attempts so that each one is a separate draw from the model. Pass
    ``first_observation`` when the environment has already been reset; otherwise
    the agent resets it.
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
        memory: MemoryBlock | None = None,
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
    memory_item_ids: Sequence[str] = (),
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
        memory_item_ids=list(memory_item_ids),
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
