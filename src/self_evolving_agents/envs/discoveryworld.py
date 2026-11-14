"""``discoveryworld``: Allen AI's DiscoveryWorld scientific-discovery environment.

The adapter renders the simulator's JSON observation as compact text, accepts
actions as JSON (the format DiscoveryWorld itself uses), and reports the task
scorecard as the ground-truth outcome.

Two things are kept strictly apart. The agent only ever sees what a player sees:
its surroundings, the result of its last action, and whether the task is marked
complete. The scorecard (sub-goal progress, normalised score) is oracle knowledge;
it is read only by ``outcome()`` and never placed in an observation or step record.

DiscoveryWorld prints verbosely and saves a rendered frame per observation; both
are redirected (stdout swallowed, frames sent to a temporary directory).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import random
import re
import shutil
import tempfile
import types
import warnings
from functools import lru_cache
from typing import Any

from ..types import Action, Observation, Outcome, Task
from .base import ActionParseError, EnvSpec, StepResult, TextEnv, register

#: Tiles that are part of every room and carry no information for the agent.
SCENERY = {"floor", "wall", "grass", "path", "sand", "dirt", "road", "fence"}

UNIT_TESTS = [
    "Small Skills: Dialog Test",
    "Small Skills: Pick and Place Test",
    "Small Skills: Pick and Give Test",
    "Small Skills: Instrument Measurement Test",
    "Small Skills: Doors Test",
    "Small Skills: Doors with Keys Test",
    "Small Skills: Navigation in a House Test",
    "Small Skills: Search Test",
    "Small Skills: Discovery Feed Test",
    "Small Skills: Moving Agents Test",
]
DISCOVERY_THEMES = [
    "Proteomics",
    "Combinatorial Chemistry",
    "Archaeology Dating",
    "Plant Nutrients",
    "Reactor Lab",
    "Lost in Translation",
    "Space Sick",
    "It's (not) Rocket Science!",
]

DEFAULT_PARAMS: dict[str, Any] = {"max_steps": 100, "nearby_limit": 40}

_DIRECTION_ACTIONS = {"MOVE_DIRECTION", "ROTATE_DIRECTION"}
_DIRECTIONS = {"north", "east", "south", "west"}


def discoveryworld_task(
    scenario: str, difficulty: str = "Normal", seed: int = 0, **params: Any
) -> Task:
    """Build a DiscoveryWorld task. Benchmark seeds are 0-4; others are unvetted upstream."""
    return Task(
        env_id="discoveryworld",
        name=f"{scenario}/{difficulty}",
        seed=seed,
        conditions={"scenario": scenario, "difficulty": difficulty},
        params=dict(params),
    )


@contextlib.contextmanager
def _quiet():
    with contextlib.redirect_stdout(io.StringIO()):
        yield


class _IntegralFloatRandom(random.Random):
    """``random.Random`` that accepts integral floats as range bounds, as Python 3.11 did.

    DiscoveryWorld 0.0.2 calls ``world.rng.randint(1e3, 1e4)`` in "It's (not) Rocket
    Science!". Python 3.10 and 3.11 accepted integral floats there (converting them
    to ints, with a deprecation warning); Python 3.12 removed that, and the scenario
    no longer loads. Converting such bounds here gives exactly the numbers the
    scenario produces under Python 3.11, from the same seed.
    """

    @staticmethod
    def _int(value: Any) -> Any:
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    def randrange(self, start: Any, stop: Any = None, step: Any = 1) -> int:  # type: ignore[override]
        return super().randrange(
            self._int(start), None if stop is None else self._int(stop), self._int(step)
        )


_COMPAT_INSTALLED = False


def install_python312_compat() -> None:
    """Give DiscoveryWorld's scenario builder the generator above (idempotent).

    Only the world generator created by ``ScenarioMaker`` is affected; every other
    use of ``random`` in DiscoveryWorld is untouched.
    """
    global _COMPAT_INSTALLED
    if _COMPAT_INSTALLED:
        return
    with _quiet():
        import discoveryworld.ScenarioMaker as scenario_maker
    module = types.ModuleType("random")
    module.__dict__.update(random.__dict__)
    module.Random = _IntegralFloatRandom  # type: ignore[attr-defined]
    scenario_maker.random = module  # type: ignore[attr-defined]
    _COMPAT_INSTALLED = True


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _object_names(ui: dict[str, Any]) -> dict[int, str]:
    """UUID to name, for every object the agent can see or carries."""
    names: dict[int, str] = {}
    for obj in (ui.get("inventoryObjects") or []) + (ui.get("accessibleEnvironmentObjects") or []):
        if _as_int(obj.get("uuid")) is not None:
            names[int(obj["uuid"])] = obj.get("name", "?")
    for objects in ((ui.get("nearbyObjects") or {}).get("objects") or {}).values():
        for obj in objects:
            if _as_int(obj.get("uuid")) is not None:
                names.setdefault(int(obj["uuid"]), obj.get("name", "?"))
    return names


@lru_cache(maxsize=256)
def _answer_key(scenario: str, difficulty: str, seed: int) -> str:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    install_python312_compat()
    with _quiet(), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        from discoveryworld.DiscoveryWorldAPI import DiscoveryWorldAPI

        frames = tempfile.mkdtemp(prefix="sea_dw_key_")
        try:
            api = DiscoveryWorldAPI(threadID=900000 + seed)
            api.FRAME_DIR = frames + "/"
            if not api.loadScenario(
                scenarioName=scenario, difficultyStr=difficulty, randomSeed=seed, numUserAgents=1
            ):
                raise ValueError(f"DiscoveryWorld could not load {scenario!r} / {difficulty!r}")
            tasks = [
                {
                    "task_name": task.taskName,
                    "task_description": task.taskDescription,
                    "critical_questions": list(task.criticalQuestions),
                    "critical_hypotheses": list(task.criticalHypotheses),
                }
                for task in api.world.taskScorer.tasks
            ]
        finally:
            shutil.rmtree(frames, ignore_errors=True)
    return json.dumps(tasks)


def answer_key(scenario: str, difficulty: str, seed: int) -> list[dict[str, Any]]:
    """The discovery a world hides: its critical questions and hypotheses.

    This is oracle knowledge, used to grade an agent's knowledge after an episode, as
    DiscoveryWorld's own knowledge scorer does. Nothing an agent is shown comes from
    here.
    """
    return json.loads(_answer_key(scenario, difficulty, int(seed)))


class DiscoveryWorldEnv(TextEnv):
    env_id = "discoveryworld"
    _next_thread_id = 1000

    def __init__(self, task: Task):
        super().__init__(task)
        self.params = {**DEFAULT_PARAMS, **task.params}
        self.scenario = task.conditions["scenario"]
        self.difficulty = task.conditions.get("difficulty", "Normal")
        self._api: Any = None
        self._frame_dir: str | None = None
        self._spec: EnvSpec | None = None
        self._task_text = ""
        self._ready = False
        self._names: dict[int, str] = {}
        self._api_observation: dict[str, Any] = {}

    # ------------------------------------------------------------------ setup

    def _load(self) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        try:
            with _quiet():
                from discoveryworld.DiscoveryWorldAPI import DiscoveryWorldAPI
        except ImportError as exc:  # pragma: no cover - depends on the optional extra
            raise ImportError(
                "discoveryworld is not installed: pip install 'self-evolving-agents[discoveryworld]'"
            ) from exc
        install_python312_compat()
        DiscoveryWorldEnv._next_thread_id += 1
        self._cleanup_frames()
        self._frame_dir = tempfile.mkdtemp(prefix="sea_dw_frames_")
        with _quiet(), warnings.catch_warnings():
            # "It's (not) Rocket Science!" overflows numpy arrays while it searches for
            # a fuel; the overflowing candidates are discarded. Upstream behaviour.
            warnings.simplefilter("ignore", RuntimeWarning)
            api = DiscoveryWorldAPI(threadID=DiscoveryWorldEnv._next_thread_id)
            # The API clears and writes PNG frames here on every observation.
            api.FRAME_DIR = self._frame_dir + "/"
            ok = api.loadScenario(
                scenarioName=self.scenario,
                difficultyStr=self.difficulty,
                randomSeed=int(self.task.seed),
                numUserAgents=1,
            )
        if not ok:
            raise ValueError(
                f"DiscoveryWorld could not load scenario {self.scenario!r} at difficulty "
                f"{self.difficulty!r}"
            )
        self._api = api

    def _cleanup_frames(self) -> None:
        if self._frame_dir and os.path.isdir(self._frame_dir):
            shutil.rmtree(self._frame_dir, ignore_errors=True)
        self._frame_dir = None

    def _build_spec(self) -> EnvSpec:
        actions = self._api.listKnownActions(limited=False)
        lines = []
        for name, info in actions.items():
            args = ", ".join(info["args"]) if info["args"] else "no arguments"
            lines.append(f"- `{name}` ({args}): {info['desc']}")
        teleports = sorted(self._api.listTeleportLocationsDict().keys())
        actions_doc = "\n".join(lines)
        actions_doc += (
            "\n\nArguments `arg1`/`arg2` are object UUIDs taken from the observation, except: "
            "MOVE_DIRECTION and ROTATE_DIRECTION take one of north/east/south/west; "
            "TELEPORT_TO_LOCATION takes a location name; DISCOVERY_FEED_GET_POST_BY_ID takes a "
            "post number."
        )
        if teleports:
            actions_doc += "\nTeleport locations: " + ", ".join(teleports) + "."
        actions_doc += "\nWhile a dialog is open you can only choose one of its numbered options."
        return EnvSpec(
            domain="scientific discovery and laboratory investigation in a simulated world",
            role=(
                "You control a scientist agent in DiscoveryWorld, a simulated colony on another "
                "planet. You explore, talk to characters, use instruments on objects and run "
                "experiments in order to complete the task you are given."
            ),
            actions_doc=actions_doc,
            observation_doc=(
                "- location: your grid position, facing direction and which moves are open.\n"
                "- inventory: objects you carry, with their UUIDs.\n"
                "- within reach: objects you can act on right now, with their UUIDs.\n"
                "- nearby: objects a few tiles away, by compass direction and distance. You must "
                "move or teleport next to them before using them.\n"
                "- last action result: what your previous action did.\n"
                "- dialog: what a character or terminal says and the replies you may choose.\n"
                "- discovery feed: recent posts on the colony's message board.\n"
                "- task status: whether the task has been marked complete."
            ),
            rules_doc=(
                "- You act once per step. The episode ends when the task is marked complete or "
                "after the step limit.\n"
                "- Objects can only be picked up, used, opened or read when they are within reach "
                "or in your inventory.\n"
                "- Some tasks end with a single irreversible choice; a wrong choice completes the "
                "task unsuccessfully."
            ),
            action_format=(
                'a JSON object such as {"action": "USE", "arg1": 1234, "arg2": 5678}; inside a '
                'dialog, {"chosen_dialog_option_int": 1}'
            ),
            success_doc=(
                "The episode is a success only if the task is marked complete and what the task "
                "asked for was actually achieved. Running out of steps, or completing the task "
                "with a wrong final answer, is a failure."
            ),
            action_names=list(actions.keys()),
        )

    # ------------------------------------------------------------------ rendering

    @staticmethod
    def _obj(o: dict[str, Any], with_distance: bool = False) -> str:
        description = o.get("description") or ""
        name = o.get("name", "?")
        text = f"[{o.get('uuid')}] {name}"
        if description and description != name:
            text += f" - {description}"
        if with_distance and "distance" in o:
            text += f" (distance {o['distance']})"
        return text

    def _render(self, ui: dict[str, Any]) -> str:
        loc = ui.get("agentLocation", {})
        lines = [f"Step {ui.get('world_steps', '?')} of at most {self.params['max_steps']}"]
        progress = ui.get("taskProgress") or []
        if progress:
            status = "complete" if all(t.get("completed") for t in progress) else "not complete"
            lines.append(f"Task status: {status}")
        lines.append(
            f"Location: ({loc.get('x')}, {loc.get('y')}), facing {loc.get('faceDirection')}; "
            f"can move {', '.join(loc.get('directions_you_can_move', [])) or 'nowhere'}"
        )
        last = (ui.get("lastActionMessage") or "").strip()
        extended = (ui.get("extended_action_message") or "").strip()
        if last:
            lines.append(f"Last action result: {last}")
        if extended and extended != last:
            lines.append(f"Message: {extended}")

        dialog = ui.get("dialog_box") or {}
        if dialog.get("is_in_dialog"):
            lines.append("DIALOG OPEN - reply with one option number.")
            said = dialog.get("dialogIn")
            if said:
                lines.append(f"  They say: {said}")
            for key, text in (dialog.get("dialogOptions") or {}).items():
                lines.append(f"  option {key}: {text}")

        inventory = ui.get("inventoryObjects") or []
        lines.append(
            "Inventory: " + ("; ".join(self._obj(o) for o in inventory) if inventory else "empty")
        )
        reach = [
            o for o in ui.get("accessibleEnvironmentObjects") or [] if o.get("name") not in SCENERY
        ]
        lines.append(
            "Within reach: " + ("; ".join(self._obj(o) for o in reach) if reach else "nothing")
        )

        nearby = (ui.get("nearbyObjects") or {}).get("objects") or {}
        shown, budget = [], int(self.params["nearby_limit"])
        for direction, objects in nearby.items():
            interesting = [o for o in objects if o.get("name") not in SCENERY]
            interesting.sort(key=lambda o: o.get("distance", 0))
            if interesting and budget > 0:
                kept = interesting[:budget]
                budget -= len(kept)
                shown.append(
                    f"  {direction}: " + "; ".join(self._obj(o, with_distance=True) for o in kept)
                )
        if shown:
            lines.append("Nearby:")
            lines.extend(shown)

        agents = (ui.get("nearbyAgents") or {}).get("list_of_agents") or {}
        if agents:
            lines.append("Nearby characters: " + json.dumps(agents)[:600])
        feed = ui.get("discoveryFeed") or {}
        posts = feed.get("posts") or []
        if posts:
            lines.append("Discovery feed:")
            for post in posts[-5:]:
                lines.append(
                    f"  #{post.get('postID')} {post.get('author')}: {str(post.get('content'))[:300]}"
                )
        return "\n".join(lines)

    def _observe(self) -> Observation:
        with _quiet():
            raw = self._api.getAgentObservation(agentIdx=0)
        if raw.get("errors"):
            raise RuntimeError(f"DiscoveryWorld observation error: {raw['errors']}")
        # What the API returns, without the rendered images: the DiscoveryWorld
        # Hypothesizer shows exactly this to its model.
        self._api_observation = {k: v for k, v in raw.items() if k != "vision"}
        ui = raw["ui"]
        self._names = _object_names(ui)
        self._in_dialog = bool((ui.get("dialog_box") or {}).get("is_in_dialog"))
        loc = ui.get("agentLocation", {})
        carried = (
            ", ".join(o.get("name", "?") for o in ui.get("inventoryObjects") or []) or "nothing"
        )
        brief = f"at ({loc.get('x')}, {loc.get('y')}) carrying {carried}"
        if self._in_dialog:
            brief += " (in dialog)"
        return Observation(text=self._render(ui), features={}, raw=ui, brief=brief)

    # ------------------------------------------------------------------ TextEnv

    @property
    def spec(self) -> EnvSpec:
        if self._spec is None:
            raise RuntimeError("call reset() first; the action list comes from the loaded scenario")
        return self._spec

    @property
    def query(self) -> str:
        if not self._task_text:
            raise RuntimeError("call reset() first; the task text comes from the loaded scenario")
        return self._task_text

    def reset(self) -> Observation:
        self._load()
        self._spec = self._build_spec()
        self._steps = 0
        self._score_trace: list[float] = []
        self._invalid_actions = 0
        observation = self._observe()
        progress = observation.raw.get("taskProgress") or []
        description = "\n".join(t.get("description", "").strip() for t in progress).strip()
        self._task_text = (
            f"DiscoveryWorld task ({self.scenario}, {self.difficulty} difficulty):\n{description}"
        )
        self._ready = True
        return observation

    def parse_action(self, text: str) -> Action:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ActionParseError("the action must be a JSON object")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ActionParseError(f"the action is not valid JSON ({exc.msg})") from None
        if not isinstance(data, dict):
            raise ActionParseError("the action must be a JSON object")

        if "chosen_dialog_option_int" in data:
            try:
                option = int(data["chosen_dialog_option_int"])
            except (TypeError, ValueError):
                raise ActionParseError("chosen_dialog_option_int must be an integer") from None
            return Action("DIALOG", {"chosen_dialog_option_int": option})

        name = str(data.get("action", "")).upper()
        known = self.spec.action_names
        if name not in known:
            raise ActionParseError(f"unknown action {name!r}; known actions: {', '.join(known)}")
        args: dict[str, Any] = {}
        for key in ("arg1", "arg2"):
            if data.get(key) is not None:
                args[key] = data[key]
        if name in _DIRECTION_ACTIONS:
            direction = str(args.get("arg1", "")).lower()
            if direction not in _DIRECTIONS:
                raise ActionParseError(f"{name} needs arg1 to be one of north, east, south, west")
            args["arg1"] = direction
        return Action(name, args)

    def fallback_action(self) -> Action:
        if getattr(self, "_in_dialog", False):
            return Action("DIALOG", {"chosen_dialog_option_int": 1})
        return Action("DISCOVERY_FEED_GET_UPDATES")

    def step(self, action: Action) -> StepResult:
        if not self._ready:
            raise RuntimeError("call reset() before step()")
        arg_names = {
            key: self._names.get(_as_int(value))
            for key, value in action.args.items()
            if key in ("arg1", "arg2") and _as_int(value) is not None
        }
        if action.name == "NOOP":
            # Time passes without an action: what the DiscoveryWorld Hypothesizer does
            # when its model's reply cannot be read.
            with _quiet():
                self._api.tick()
            result = {"success": False, "errors": [action.args.get("reason", "no action taken")]}
        else:
            if action.name == "DIALOG":
                payload = dict(action.args)
            else:
                payload = {"action": action.name, "arg1": None, "arg2": None, **action.args}
            with _quiet():
                result = self._api.performAgentAction(agentIdx=0, actionJSON=payload)
                self._api.tick()
        self._steps += 1
        success = bool(result.get("success"))
        if not success:
            self._invalid_actions += 1
        observation = self._observe()
        with _quiet():
            complete = bool(self._api.areTasksComplete())
            scorecard = self._api.getTaskScorecard() or []
        if scorecard:
            self._score_trace.append(float(scorecard[0].get("scoreNormalized", 0.0)))
        truncated = (not complete) and self._steps >= int(self.params["max_steps"])
        info = {
            "action_ok": success,
            "errors": [str(e) for e in result.get("errors") or []][:3],
            "arg_names": arg_names,
        }
        summary = " ".join((observation.raw.get("lastActionMessage") or "").split())
        if not summary:
            summary = "action accepted" if success else "action had no effect or was invalid"
        event = ""
        if complete:
            event = "Episode over: the task has been marked complete."
        elif truncated:
            event = "Episode over: step limit reached before the task was completed."
        return StepResult(
            observation, 0.0, complete, truncated, info, summary=summary[:400], event=event
        )

    def outcome(self) -> Outcome:
        with _quiet():
            scorecard = self._api.getTaskScorecard() or []
        card = scorecard[0] if scorecard else {}
        completed = bool(card.get("completed"))
        succeeded = bool(card.get("completedSuccessfully"))
        failure = None
        if completed and not succeeded:
            failure = "wrong_answer"
        elif not completed:
            failure = "incomplete"
        subgoals = card.get("scoreCard") or []
        return Outcome(
            score=float(card.get("scoreNormalized", 0.0)),
            success=succeeded,
            failure=failure,
            terminated=completed,
            truncated=not completed,
            metrics={
                "completed": completed,
                "completed_successfully": succeeded,
                "n_steps": self._steps,
                "invalid_actions": self._invalid_actions,
                "subgoals_done": sum(1 for g in subgoals if g.get("completed")),
                "subgoals_total": len(subgoals),
                "score_trace": self._score_trace,
            },
        )

    # ------------------------------------------------------------------ for agents that
    # use the API's own formats (the DiscoveryWorld Hypothesizer)

    def api_observation(self) -> dict[str, Any]:
        """The last observation as the API returned it, without the rendered images."""
        if not self._ready:
            raise RuntimeError("call reset() first")
        return self._api_observation

    def known_actions(self) -> dict[str, Any]:
        with _quiet():
            return self._api.listKnownActions(limited=False)

    def action_help(self) -> str:
        with _quiet():
            return self._api.additionalActionDescriptionString()

    def teleport_locations(self) -> dict[str, Any]:
        with _quiet():
            return self._api.listTeleportLocationsDict()

    def in_dialog(self) -> bool:
        with _quiet():
            return bool(self._api.isAgentInDialog(agentIdx=0))

    @property
    def world(self) -> dict[str, Any]:
        """Which world this is: scenario, difficulty and seed."""
        return {"scenario": self.scenario, "difficulty": self.difficulty, "seed": self.task.seed}

    def close(self) -> None:
        self._api = None
        self._ready = False
        self._cleanup_frames()


register(DiscoveryWorldEnv.env_id, DiscoveryWorldEnv)
