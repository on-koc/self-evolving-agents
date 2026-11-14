"""DiscoveryWorld's random baseline (``agents/RandomAgent.py``), ported.

At every step: inside a dialog, a random option; otherwise a random action from the
full action list, with random objects from those within reach as its arguments, a
random direction, teleport location or post number where the action takes one. No
model is involved, and the agent reads no memory.

The random draws are made in the original's order. The original seeds its generator
from the clock; the port seeds it from ``seed``, the task and the attempt, so that an
episode can be repeated. Where the original crashes (an action that needs an object
when none is within reach; its batch runner then restarts the episode with a new
clock seed), the port leaves the argument empty and the game rejects the action.
"""

from __future__ import annotations

import random
import time
from typing import Any

from ...envs.base import TextEnv
from ...types import Action, Observation, Step, Trajectory
from ..base import Agent, MemoryBlock, run_episode

DIRECTIONS = ["north", "east", "south", "west"]


def random_action(rng: random.Random, env: Any, observation: dict[str, Any]) -> dict[str, Any]:
    """One step of ``randomAgent``: the JSON it sends to the game."""
    ui = observation["ui"]
    if env.in_dialog():
        options = list(ui["dialog_box"]["dialogOptions"].keys())
        chosen = rng.choice(options)
        try:
            chosen_int = int(chosen)
        except (TypeError, ValueError):
            chosen_int = random.randint(1, len(options) + 1)  # as released: the module generator
        return {"chosen_dialog_option_int": chosen_int}

    accessible = list(ui["inventoryObjects"]) + list(ui["accessibleEnvironmentObjects"])
    actions = env.known_actions()
    name = rng.choice(list(actions.keys()))
    action: dict[str, Any] = {"action": name, "arg1": None, "arg2": None}
    for arg in actions[name]["args"]:
        if accessible:
            action[arg] = rng.choice(accessible)["uuid"]
    if name in ("MOVE_DIRECTION", "ROTATE_DIRECTION"):
        action["arg1"] = rng.choice(DIRECTIONS)
    elif name == "TELEPORT_TO_LOCATION":
        action["arg1"] = rng.choice(list(env.teleport_locations().keys()))
    elif name == "DISCOVERY_FEED_GET_POST_BY_ID":
        action["arg1"] = rng.randint(1, 100)
    return action


class RandomAgent(Agent):
    """DiscoveryWorld's random agent.

    Args:
        llm: ignored (accepted so that every agent is built the same way).
        seed: base of the random generator; the task and the attempt are mixed in.
        rng_seed: seed the generator with exactly this number in every episode, as the
            original's ``randomAgent(api, numSteps, seed)`` does (then ``seed`` is not
            used).
    """

    kind = "random"

    def __init__(self, llm: Any = None, *, seed: int = 0, rng_seed: int | None = None):
        self.seed = int(seed)
        self.rng_seed = rng_seed

    @property
    def descriptor(self) -> dict[str, Any]:
        return {
            "id": f"random:{self.seed if self.rng_seed is None else self.rng_seed}",
            "kind": self.kind,
            "seed": self.seed,
            "rng_seed": self.rng_seed,
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
        for needed in ("api_observation", "known_actions", "teleport_locations", "in_dialog"):
            if not hasattr(env, needed):
                raise TypeError("the random agent needs the DiscoveryWorld environment")
        if first_observation is None:
            first_observation = env.reset()
        rng = random.Random()
        if self.rng_seed is not None:
            rng.seed(self.rng_seed)
        else:
            rng.seed(f"discoveryworld-random:{self.seed}:{env.task.key}:{sample}")
        started = time.time()

        def decide(
            observation: Observation, steps: list[Step]
        ) -> tuple[str, Action, str | None, dict[str, Any]]:
            chosen = random_action(rng, env, env.api_observation())  # type: ignore[attr-defined]
            if "chosen_dialog_option_int" in chosen:
                action = Action("DIALOG", dict(chosen), payload=chosen)
            else:
                args = {k: chosen[k] for k in ("arg1", "arg2") if chosen.get(k) is not None}
                action = Action(chosen["action"], args, payload=chosen)
            return "", action, None, {}

        traj = run_episode(
            env,
            decide,
            agent=self.descriptor,
            first_observation=first_observation,
            memory_item_ids=(memory.item_ids if memory else ()),
            meta=meta,
        )
        traj.meta["knowledge_text"] = ""
        traj.meta["agent_seconds"] = round(time.time() - started, 2)
        return traj
