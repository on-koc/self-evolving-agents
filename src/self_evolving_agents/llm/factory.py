"""Build an LLM backend from a short spec string, e.g. ``anthropic:claude-opus-5-5``."""

from __future__ import annotations

from typing import Any

from .base import LLMBackend, LLMError


def make_backend(spec: str, **options: Any) -> LLMBackend:
    """Create a backend.

    Specs:

    * ``anthropic`` or ``anthropic:<model>`` – Claude through the official SDK. A bare
      ``claude-...`` model id is accepted as shorthand.
    * ``offline-demo`` – the rule-based stand-in from :mod:`.offline`. Not a language
      model; it exists to exercise the pipeline without credentials or cost.
    """
    provider, _, model = spec.partition(":")
    if provider.startswith("claude-"):
        provider, model = "anthropic", provider
    if provider == "anthropic":
        from .anthropic_backend import DEFAULT_MODEL, AnthropicBackend

        return AnthropicBackend(model or DEFAULT_MODEL, **options)
    if provider == "offline-demo":
        from .offline import OfflineDemoLLM

        return OfflineDemoLLM(**options)
    raise LLMError(
        f"unknown LLM spec {spec!r}; use 'anthropic[:model]' or 'offline-demo'"
    )
