"""Build a model backend from a short description, e.g. ``ollama:llama3.2:3b``."""

from __future__ import annotations

from typing import Any

from .base import LLMBackend, LLMError
from .specs import split_spec

#: The providers ``make_backend`` knows, with what each one is.
PROVIDERS = {
    "anthropic": "Claude through the Anthropic API (official SDK)",
    "openai": "any server speaking the OpenAI chat-completions protocol (official SDK)",
    "ollama": "a model served by Ollama, through its own API (official client)",
    "hf": "a model run on this machine with Hugging Face transformers",
    "offline-demo": "a rule-based stand-in, not a language model; for dry runs only",
}


def is_stand_in(spec: str) -> bool:
    """Whether a description names the rule-based stand-in instead of a language model."""
    return split_spec(spec)[0].startswith("offline")


def make_backend(spec: str, **options: Any) -> LLMBackend:
    """Create a backend.

    Descriptions:

    * ``anthropic`` or ``anthropic:<model>``: Claude. A bare ``claude-...`` model id is
      accepted as shorthand.
    * ``openai:<model>`` or ``openai:<model>@<address>``: an OpenAI-compatible server
      (OpenAI, vLLM, llama.cpp, LM Studio, Together, the Hugging Face router, ...).
    * ``ollama:<model>`` or ``ollama:<model>@<address>``: an Ollama server.
    * ``hf:<model>``: a model loaded with ``transformers`` on this machine.
    * ``offline-demo``: the rule-based stand-in from :mod:`.offline`.

    ``options`` are passed to the backend's constructor; each backend documents its own.
    """
    provider, model, address = split_spec(spec)
    if provider.startswith("claude-"):
        provider, model = "anthropic", provider
    if provider == "anthropic":
        from .anthropic_backend import DEFAULT_MODEL, AnthropicBackend

        return _build(AnthropicBackend, model or DEFAULT_MODEL, options, spec)
    if provider == "openai":
        from .openai_backend import OpenAIBackend

        if address:
            options = {"base_url": address, **options}
        options.pop("effort", None)
        return _build(OpenAIBackend, model, options, spec)
    if provider == "ollama":
        from .ollama_backend import OllamaBackend

        if address:
            options = {"host": address, **options}
        options.pop("effort", None)
        return _build(OllamaBackend, model, options, spec)
    if provider == "hf":
        from .huggingface_backend import HuggingFaceBackend

        options.pop("effort", None)
        return _build(HuggingFaceBackend, model, options, spec)
    if provider == "offline-demo":
        from .offline import OfflineDemoLLM

        options.pop("effort", None)
        return _build(OfflineDemoLLM, None, options, spec)
    known = ", ".join(f"'{name}'" for name in PROVIDERS)
    raise LLMError(f"unknown model description {spec!r}; the provider must be one of {known}")


def _build(cls: Any, model: str | None, options: dict[str, Any], spec: str) -> LLMBackend:
    try:
        return cls(**options) if model is None else cls(model, **options)
    except TypeError as exc:
        # An option the backend does not have: say which, instead of a constructor traceback.
        raise LLMError(f"{spec}: {exc}. Options given: {sorted(options)}") from exc
