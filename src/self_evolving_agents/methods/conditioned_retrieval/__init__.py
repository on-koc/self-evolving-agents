"""Condition-aware ReasoningBank: an adaptation of retrieval and extraction for simulation regimes.

Not part of the published method and not evaluated with a language model. See
``docs/methods/conditioned_retrieval.md``.
"""

from .bank import ConditionedBank
from .method import (
    CONDITION_NOTES,
    ConditionedConfig,
    ConditionedExtractor,
    ConditionedMemory,
    build,
)

__all__ = [
    "CONDITION_NOTES",
    "ConditionedBank",
    "ConditionedConfig",
    "ConditionedExtractor",
    "ConditionedMemory",
    "build",
]
