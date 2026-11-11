"""Claude backend, built on the official ``anthropic`` SDK.

Notes that are easy to get wrong with current Claude models:

* Sampling parameters (``temperature``, ``top_p``, ``top_k``) are no longer accepted
  by the Messages API, so the request's temperature hint is dropped here. The
  paper's "judge at T=0, extract at T=1" split therefore cannot be reproduced on
  Claude; replay determinism comes from the response cache in ``TrackedLLM`` instead.
* Thinking is adaptive and on by default; depth is steered with ``effort``.
* A request can come back with ``stop_reason == "refusal"``. For the model families
  that support it, server-side fallbacks are requested by default so that a
  declined step is retried on another model inside the same call.
"""

from __future__ import annotations

import time
from typing import Any

from .base import LLMError, LLMRefusal, LLMRequest, LLMResponse, Usage

DEFAULT_MODEL = "claude-opus-5-5"

# Models for which the API offers server-side refusal fallbacks.
_FALLBACK_PREFIXES = (
    "claude-fable-5",
    "claude-opus-5",
    "claude-sonnet-5-5",
)
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicBackend:
    """Sends :class:`LLMRequest` objects to the Claude Messages API.

    Credentials are resolved by the SDK (``ANTHROPIC_API_KEY``, ``ANTHROPIC_AUTH_TOKEN``
    or an ``ant auth login`` profile); nothing is read or stored here.

    Args:
        model: Claude model id.
        effort: ``low`` | ``medium`` | ``high`` | ``xhigh`` | ``max``; ``None`` keeps the
            model's own default.
        refusal_fallback: ask the API to rerun a declined request on a fallback model.
            Only sent for model families that support it.
        cache_system_prompt: mark the system prompt as a prompt-cache breakpoint. The
            system prompt is identical for every step of an episode, so later steps
            read it from the cache when it is long enough to be cacheable.
        max_retries: SDK-level retries for rate limits, timeouts and server errors.
        client: an already constructed ``anthropic.Anthropic`` (used by tests).
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        effort: str | None = None,
        refusal_fallback: bool = True,
        cache_system_prompt: bool = True,
        max_retries: int = 5,
        client: Any = None,
    ):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise LLMError(
                "The Claude backend needs the anthropic SDK: pip install 'self-evolving-agents[anthropic]'"
            ) from exc
        self._anthropic = anthropic
        self.model = model
        self.effort = effort
        self.cache_system_prompt = cache_system_prompt
        self.refusal_fallback = refusal_fallback and model.startswith(_FALLBACK_PREFIXES)
        self.client = client if client is not None else anthropic.Anthropic(max_retries=max_retries)

    def _params(self, request: LLMRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": m["role"], "content": m["content"]} for m in request.messages],
        }
        if request.system:
            block: dict[str, Any] = {"type": "text", "text": request.system}
            if self.cache_system_prompt:
                block["cache_control"] = {"type": "ephemeral"}
            params["system"] = [block]
        if self.effort:
            params["output_config"] = {"effort": self.effort}
        return params

    def complete(self, request: LLMRequest) -> LLMResponse:
        anthropic = self._anthropic
        params = self._params(request)
        started = time.time()
        try:
            if self.refusal_fallback:
                message = self.client.beta.messages.create(
                    betas=[_FALLBACK_BETA], fallbacks="default", **params
                )
            else:
                message = self.client.messages.create(**params)
        except anthropic.AuthenticationError as exc:
            raise LLMError(
                "Claude rejected the credentials. Set ANTHROPIC_API_KEY or run `ant auth login`."
            ) from exc
        except anthropic.PermissionDeniedError as exc:
            raise LLMError(f"Credential lacks permission for {self.model}: {exc.message}") from exc
        except anthropic.NotFoundError as exc:
            raise LLMError(f"Unknown model or endpoint ({self.model}): {exc.message}") from exc
        except anthropic.BadRequestError as exc:
            raise LLMError(f"Claude rejected the request: {exc.message}") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError(f"Still rate limited after retries: {exc.message}") from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Claude API error {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"Could not reach the Claude API: {exc}") from exc

        if message.stop_reason == "refusal":
            details = getattr(message, "stop_details", None)
            category = getattr(details, "category", None)
            raise LLMRefusal(f"model declined the request (category: {category})")

        text = "".join(block.text for block in message.content if block.type == "text")
        usage = message.usage
        return LLMResponse(
            text=text,
            model=message.model or self.model,
            usage=Usage(
                input_tokens=usage.input_tokens or 0,
                output_tokens=usage.output_tokens or 0,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            ),
            stop_reason=message.stop_reason or "end_turn",
            latency_s=time.time() - started,
        )
