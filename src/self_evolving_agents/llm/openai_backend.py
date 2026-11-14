"""Any server that speaks the OpenAI chat-completions protocol, through the official SDK.

That covers OpenAI itself and the many servers that imitate it: vLLM, llama.cpp,
LM Studio, text-generation-inference, Ollama's ``/v1`` endpoint, Together, Groq,
OpenRouter, the Hugging Face router. The address is the only thing that differs.

Unlike current Claude models, these servers accept a decoding temperature, so the
temperatures a method asks for (ReasoningBank: 0.7 for acting, 0.0 for judging, 1.0
for extraction) are applied here, and reported in ``LLMResponse.meta``.
"""

from __future__ import annotations

import os
import time
from typing import Any

from .base import LLMError, LLMRefusal, LLMRequest, LLMResponse, Usage

_STOP_REASONS = {"stop": "end_turn", "length": "max_tokens", "tool_calls": "tool_use"}


class OpenAIBackend:
    """Sends :class:`LLMRequest` objects to a chat-completions endpoint.

    Args:
        model: the model name the server knows.
        base_url: address of the server, ending in ``/v1`` for most of them. ``None``
            lets the SDK use ``OPENAI_BASE_URL`` or OpenAI's own address.
        api_key_env: name of the environment variable holding the key. The key is read
            by this process and never logged. A local server that needs no key works
            without the variable being set.
        honour_temperature: send the request's temperature. Switch off for models that
            reject it (some reasoning models accept only their default).
        max_tokens_param: ``max_tokens`` (most servers) or ``max_completion_tokens``
            (newer OpenAI models).
        max_output_tokens: upper limit on the reply length sent to the server, for
            servers that refuse a limit larger than their context window.
        seed: if set, ``seed + request.sample`` is sent, which makes replies repeatable
            on servers that honour a seed.
        reasoning_effort: passed through for models that take it.
        price_in, price_out: USD per million tokens, for the spend estimate and the
            cost limit. Leave unset if unknown; set both to 0 for a local server.
        extra_body: additional JSON fields for servers with their own extensions.
        client: an already constructed ``openai.OpenAI`` (used by tests).
    """

    def __init__(
        self,
        model: str,
        *,
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        honour_temperature: bool = True,
        max_tokens_param: str = "max_tokens",
        max_output_tokens: int | None = None,
        seed: int | None = None,
        reasoning_effort: str | None = None,
        price_in: float | None = None,
        price_out: float | None = None,
        extra_body: dict[str, Any] | None = None,
        timeout: float = 600.0,
        max_retries: int = 5,
        client: Any = None,
    ):
        if not model:
            raise LLMError("an OpenAI-compatible backend needs a model name: openai:<model>")
        if max_tokens_param not in ("max_tokens", "max_completion_tokens"):
            raise LLMError("max_tokens_param must be 'max_tokens' or 'max_completion_tokens'")
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise LLMError(
                "The OpenAI-compatible backend needs the openai SDK: "
                "pip install 'self-evolving-agents[openai]'"
            ) from exc
        self._openai = openai
        self.model = model
        self.base_url = base_url
        self.honour_temperature = honour_temperature
        self.max_tokens_param = max_tokens_param
        self.max_output_tokens = max_output_tokens
        self.seed = seed
        self.reasoning_effort = reasoning_effort
        self.extra_body = dict(extra_body or {})
        self.price_per_mtok = (
            (float(price_in), float(price_out))
            if price_in is not None and price_out is not None
            else None
        )
        if client is None:
            # A server on the local machine usually wants no key, but the SDK insists on one.
            key = os.environ.get(api_key_env) or ("not-needed" if base_url else None)
            try:
                client = openai.OpenAI(
                    api_key=key, base_url=base_url, timeout=timeout, max_retries=max_retries
                )
            except openai.OpenAIError as exc:
                raise LLMError(
                    f"cannot set up the OpenAI client: {exc} Set {api_key_env} in the "
                    "environment, or give the address of your own server "
                    "(openai:<model>@http://host:port/v1)."
                ) from exc
        self.client = client

    # -- what decides the reply besides the prompt ----------------------------------

    def _temperature(self, request: LLMRequest) -> float | None:
        return request.temperature if self.honour_temperature else None

    def _seed(self, request: LLMRequest) -> int | None:
        return None if self.seed is None else int(self.seed) + int(request.sample)

    def signature(self, request: LLMRequest) -> dict[str, Any]:
        return {
            "endpoint": self.base_url,
            "temperature": self._temperature(request),
            "seed": self._seed(request),
            "reasoning_effort": self.reasoning_effort,
            "extra_body": self.extra_body or None,
        }

    def _params(self, request: LLMRequest) -> dict[str, Any]:
        messages = [{"role": m["role"], "content": m["content"]} for m in request.messages]
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        limit = request.max_tokens
        if self.max_output_tokens is not None:
            limit = min(limit, int(self.max_output_tokens))
        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            self.max_tokens_param: limit,
        }
        temperature = self._temperature(request)
        if temperature is not None:
            params["temperature"] = float(temperature)
        seed = self._seed(request)
        if seed is not None:
            params["seed"] = seed
        if self.reasoning_effort:
            params["reasoning_effort"] = self.reasoning_effort
        if self.extra_body:
            params["extra_body"] = self.extra_body
        return params

    def complete(self, request: LLMRequest) -> LLMResponse:
        openai = self._openai
        params = self._params(request)
        where = self.base_url or "the OpenAI API"
        started = time.time()
        try:
            completion = self.client.chat.completions.create(**params)
        except openai.AuthenticationError as exc:
            raise LLMError(
                f"{where} rejected the credentials. Set the API key in the environment "
                "(OPENAI_API_KEY, or the variable named by the api_key_env option)."
            ) from exc
        except openai.PermissionDeniedError as exc:
            raise LLMError(f"credential lacks permission for {self.model}: {exc}") from exc
        except openai.NotFoundError as exc:
            raise LLMError(f"{where} does not know model {self.model!r}: {exc}") from exc
        except openai.BadRequestError as exc:
            hint = ""
            text = str(exc).lower()
            if "temperature" in text:
                hint = " If the model accepts no temperature, set honour_temperature=false."
            elif "max_tokens" in text or "max_completion_tokens" in text or "context" in text:
                hint = (
                    " Try max_tokens_param=max_completion_tokens, or lower the reply limit "
                    "with max_output_tokens=<n>."
                )
            raise LLMError(f"{where} rejected the request: {exc}.{hint}") from exc
        except openai.RateLimitError as exc:
            raise LLMError(f"still rate limited after retries: {exc}") from exc
        except openai.APIStatusError as exc:
            raise LLMError(f"{where} returned an error ({exc.status_code}): {exc}") from exc
        except openai.APIConnectionError as exc:
            raise LLMError(f"could not reach {where}: {exc}") from exc

        if not completion.choices:
            raise LLMError(f"{where} returned no choices for model {self.model}")
        choice = completion.choices[0]
        message = choice.message
        finish = choice.finish_reason or "stop"
        refusal = getattr(message, "refusal", None)
        if refusal or finish == "content_filter":
            raise LLMRefusal(f"model declined the request: {refusal or 'content filter'}")
        text = message.content or ""
        if not text.strip() and finish == "length":
            raise LLMError(
                f"{self.model} used its whole reply limit ({params[self.max_tokens_param]} tokens) "
                "without producing any text. Raise the limit, or lower the reasoning effort."
            )
        usage = completion.usage
        details = getattr(usage, "prompt_tokens_details", None) if usage else None
        cached = int(getattr(details, "cached_tokens", 0) or 0) if details else 0
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        return LLMResponse(
            text=text,
            model=getattr(completion, "model", None) or self.model,
            usage=Usage(
                input_tokens=max(prompt_tokens - cached, 0),
                output_tokens=int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0,
                cache_read_tokens=cached,
            ),
            stop_reason=_STOP_REASONS.get(finish, finish),
            latency_s=time.time() - started,
            meta={
                "temperature": params.get("temperature"),
                "seed": params.get("seed"),
                "finish_reason": finish,
            },
        )
