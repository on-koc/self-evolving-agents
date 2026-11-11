"""The environment contract.

An environment adapter turns a simulator into something a language model can act
in: a textual observation, a documented action vocabulary and a parser for the
model's reply. It also exposes named numeric features so that rule policies can
act without a model, and reports ground-truth outcome metrics at the end.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from ..types import Action, Observation, Outcome, Task


class ActionParseError(ValueError):
    """The agent's reply could not be turned into a valid action."""


@dataclass
class EnvSpec:
    """Static documentation of an environment, used to build prompts.

    The text here states facts an operator's handbook would state (what the actions
    are, what the readings mean, what ends an episode). It deliberately contains no
    strategy advice: working out *when* to do what is the agent's job, and the thing
    memory is supposed to improve.
    """

    domain: str
    role: str
    actions_doc: str
    observation_doc: str
    rules_doc: str
    action_format: str
    success_doc: str = ""
    action_names: list[str] = field(default_factory=list)
    feature_docs: dict[str, str] = field(default_factory=dict)

    @property
    def feature_names(self) -> list[str]:
        return list(self.feature_docs)

    def instructions(self) -> str:
        return "\n\n".join(
            [
                self.role,
                "## Actions\n" + self.actions_doc,
                "## Observations\n" + self.observation_doc,
                "## Rules\n" + self.rules_doc,
            ]
        )


@dataclass
class StepResult:
    """Result of one action.

    ``summary`` is a one-line account of what the action did, and ``event`` a message
    for anything the agent must be told (in particular why the episode ended). Both
    are agent-visible. ``info`` is for diagnostics and is never shown to a model.
    """

    observation: Observation
    reward: float
    terminated: bool
    truncated: bool
    info: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    event: str = ""

    @property
    def done(self) -> bool:
        return self.terminated or self.truncated


class TextEnv(ABC):
    """Base class for environment adapters. One instance runs one task at a time."""

    env_id: ClassVar[str] = ""

    def __init__(self, task: Task):
        if task.env_id != self.env_id:
            raise ValueError(f"task is for {task.env_id!r}, not {self.env_id!r}")
        self.task = task

    @property
    @abstractmethod
    def spec(self) -> EnvSpec: ...

    @property
    @abstractmethod
    def query(self) -> str:
        """The task statement shown to the agent and used as the retrieval query."""

    @abstractmethod
    def reset(self) -> Observation: ...

    @abstractmethod
    def step(self, action: Action) -> StepResult: ...

    @abstractmethod
    def parse_action(self, text: str) -> Action:
        """Turn the contents of an ``<action>`` block into an :class:`Action`.

        Raises :class:`ActionParseError` with a message that can be shown to the agent.
        """

    @abstractmethod
    def fallback_action(self) -> Action:
        """A harmless action to take when the agent's reply cannot be used."""

    @abstractmethod
    def outcome(self) -> Outcome:
        """Ground-truth result of the episode so far."""

    def retask(self, task: Task) -> bool:
        """Reuse this instance for ``task`` if only the seed differs.

        Simulators can be expensive to construct, so batch runners keep one adapter
        per configuration and call this between episodes. Returns ``False`` when the
        adapter cannot be reused, in which case the caller builds a new one.
        """
        return False

    def close(self) -> None:  # noqa: B027 - optional hook
        """Release simulator resources."""

    def __enter__(self) -> TextEnv:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def match_action_name(text: str, names: list[str], aliases: dict[str, str] | None = None) -> str:
    """Resolve free text to exactly one of ``names``.

    Accepts the bare name in any case, surrounded by punctuation or quotes, or one of
    the given aliases. Rejects replies that mention several different actions.
    """
    cleaned = text.strip().strip("`'\"*. \n").lower()
    lookup = {n.lower(): n for n in names}
    for alias, target in (aliases or {}).items():
        lookup[alias.lower()] = target
    if cleaned in lookup:
        return lookup[cleaned]
    found = {
        lookup[key] for key in lookup if re.search(rf"(?<![a-z_]){re.escape(key)}(?![a-z_])", cleaned)
    }
    if len(found) == 1:
        return found.pop()
    if not found:
        raise ActionParseError(f"'{text.strip()[:60]}' is not one of: {', '.join(names)}")
    raise ActionParseError(
        f"reply names several actions ({', '.join(sorted(found))}); give exactly one of: "
        + ", ".join(names)
    )


_REGISTRY: dict[str, Callable[[Task], TextEnv]] = {}


def register(env_id: str, factory: Callable[[Task], TextEnv]) -> None:
    _REGISTRY[env_id] = factory


def available_envs() -> list[str]:
    _load_builtin()
    return sorted(_REGISTRY)


def make_env(task: Task) -> TextEnv:
    """Construct the adapter registered for ``task.env_id``."""
    _load_builtin()
    try:
        factory = _REGISTRY[task.env_id]
    except KeyError:
        raise KeyError(
            f"unknown environment {task.env_id!r}; available: {', '.join(sorted(_REGISTRY))}"
        ) from None
    return factory(task)


def _load_builtin() -> None:
    # Importing the modules registers them. Heavy simulators are imported lazily
    # inside each adapter, so this is cheap and never fails for a missing extra.
    from . import bsk_scan, discoveryworld, toy  # noqa: F401
