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
from .discoveryworld import discoveryworld_task
from .scanning import REGIMES, scan_task

__all__ = [
    "REGIMES",
    "ActionParseError",
    "EnvSpec",
    "StepResult",
    "TextEnv",
    "available_envs",
    "discoveryworld_task",
    "make_env",
    "register",
    "scan_task",
]
