"""Environment adapters: simulators presented as text-and-features environments."""

from .base import (
    ActionParseError,
    EnvSpec,
    StepResult,
    TextEnv,
    available_envs,
    make_env,
    register,
)
from .discoveryworld import DISCOVERY_THEMES, answer_key, discoveryworld_task
from .scanning import REGIMES, scan_task

__all__ = [
    "DISCOVERY_THEMES",
    "REGIMES",
    "ActionParseError",
    "EnvSpec",
    "StepResult",
    "TextEnv",
    "answer_key",
    "available_envs",
    "discoveryworld_task",
    "make_env",
    "register",
    "scan_task",
]
