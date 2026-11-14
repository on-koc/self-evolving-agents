"""Reading model descriptions such as ``openai:gpt-4o-mini@http://localhost:8000/v1``.

One format serves language models and embedders, on the command line and in protocol
files: ``provider:model``, optionally followed by ``@`` and the address of the server.
Everything else a backend accepts is passed as options (``--llm-option key=value``,
or ``"llm_options": {...}`` in a protocol).
"""

from __future__ import annotations

import json
from typing import Any

#: Other spellings of a provider that are accepted.
ALIASES = {
    "huggingface": "hf",
    "transformers": "hf",
    "openai-compatible": "openai",
    "claude": "anthropic",
}


def split_spec(spec: str) -> tuple[str, str, str | None]:
    """``(provider, model, address)`` of a description.

    The address is recognised by its scheme, so that an ``@`` inside a model name is
    left alone. Model names may contain colons (``llama3.2:3b``) and slashes
    (``Qwen/Qwen2.5-1.5B-Instruct``).
    """
    provider, _, rest = spec.strip().partition(":")
    provider = ALIASES.get(provider.lower(), provider.lower())
    address = None
    for scheme in ("@http://", "@https://"):
        if scheme in rest:
            rest, _, tail = rest.rpartition(scheme)
            address = scheme[1:] + tail
            break
    return provider, rest, address


def parse_options(pairs: list[str] | None) -> dict[str, Any]:
    """``["num_ctx=16384", "think=false"]`` as a dictionary.

    A value is read as JSON when it is valid JSON (numbers, ``true``, ``null``, lists,
    objects) and kept as text otherwise.
    """
    options: dict[str, Any] = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep or not key.strip():
            raise ValueError(f"expected key=value, got {pair!r}")
        try:
            options[key.strip()] = json.loads(value)
        except json.JSONDecodeError:
            options[key.strip()] = value
    return options
