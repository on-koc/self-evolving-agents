"""Language-model access: a small provider-neutral interface with tracking on top."""

from .base import (
    Budget,
    BudgetExceeded,
    LLMBackend,
    LLMError,
    LLMRefusal,
    LLMRequest,
    LLMResponse,
    TrackedLLM,
    Usage,
    assistant,
    estimate_cost_usd,
    user,
)
from .factory import PROVIDERS, is_stand_in, make_backend
from .parsing import extract_json_object
from .scripted import ScriptedLLM
from .specs import parse_options, split_spec

__all__ = [
    "Budget",
    "BudgetExceeded",
    "LLMBackend",
    "LLMError",
    "LLMRefusal",
    "LLMRequest",
    "LLMResponse",
    "PROVIDERS",
    "ScriptedLLM",
    "TrackedLLM",
    "Usage",
    "assistant",
    "estimate_cost_usd",
    "extract_json_object",
    "is_stand_in",
    "make_backend",
    "parse_options",
    "split_spec",
    "user",
]
