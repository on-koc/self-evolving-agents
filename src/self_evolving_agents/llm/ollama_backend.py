"""Models served by Ollama, through its own API and the official ``ollama`` client.

Two things are easy to get wrong with Ollama and are handled here.

* **Context length.** Ollama's default context window is small, and a prompt that
  does not fit is cut without an error. A run whose prompts were cut silently is
  worthless, so the window is set explicitly on every call (``num_ctx``) and a call
  whose prompt filled it is refused.
* **Reply length.** The limit a method asks for is sized for hosted models. It is
  capped here (``max_output_tokens``) so that the reply cannot claim the whole window.

The model runs on the user's own machine or server; its cost is counted as zero.
"""

from __future__ import annotations

import time
from typing import Any

from .base import LLMError, LLMRequest, LLMResponse, Usage


class OllamaBackend:
    """Sends :class:`LLMRequest` objects to an Ollama server (``/api/chat``).

    Args:
        model: a model the server has pulled, e.g. ``llama3.2:3b``.
        host: address of the server. ``None`` lets the client use ``OLLAMA_HOST`` or
            ``http://127.0.0.1:11434``.
        num_ctx: context window in tokens, sent with every call.
        max_output_tokens: upper limit on the reply length.
        seed: if set, ``seed + request.sample`` is sent, which makes replies repeatable.
        think: for models with a thinking mode: ``True``, ``False`` or a level. ``None``
            leaves the model's default.
        keep_alive: how long the server keeps the model loaded between calls.
        options: further Ollama options (``top_p``, ``repeat_penalty``, ...).
        strict_context: refuse a call whose prompt filled the context window.
        client: an already constructed ``ollama.Client`` (used by tests).
    """

    price_per_mtok = (0.0, 0.0)

    def __init__(
        self,
        model: str,
        *,
        host: str | None = None,
        num_ctx: int = 8192,
        max_output_tokens: int = 2048,
        seed: int | None = None,
        think: bool | str | None = None,
        keep_alive: float | str | None = None,
        options: dict[str, Any] | None = None,
        strict_context: bool = True,
        timeout: float = 600.0,
        client: Any = None,
    ):
        if not model:
            raise LLMError("an Ollama backend needs a model name: ollama:<model>")
        try:
            import ollama
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise LLMError(
                "The Ollama backend needs the ollama client: "
                "pip install 'self-evolving-agents[ollama]'"
            ) from exc
        self._ollama = ollama
        self.model = model
        self.host = host
        self.num_ctx = int(num_ctx)
        self.max_output_tokens = int(max_output_tokens)
        self.seed = seed
        self.think = think
        self.keep_alive = keep_alive
        self.options = dict(options or {})
        self.strict_context = strict_context
        self.client = client if client is not None else ollama.Client(host=host, timeout=timeout)

    def _options(self, request: LLMRequest) -> dict[str, Any]:
        options: dict[str, Any] = {
            "num_ctx": self.num_ctx,
            "num_predict": min(int(request.max_tokens), self.max_output_tokens),
        }
        if request.temperature is not None:
            options["temperature"] = float(request.temperature)
        if self.seed is not None:
            options["seed"] = int(self.seed) + int(request.sample)
        options.update(self.options)
        return options

    def signature(self, request: LLMRequest) -> dict[str, Any]:
        return {"host": self.host, "options": self._options(request), "think": self.think}

    def complete(self, request: LLMRequest) -> LLMResponse:
        ollama = self._ollama
        messages = [{"role": m["role"], "content": m["content"]} for m in request.messages]
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        options = self._options(request)
        where = self.host or "the Ollama server"
        started = time.time()
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=False,
                think=self.think,
                options=options,
                keep_alive=self.keep_alive,
            )
        except ollama.ResponseError as exc:
            if exc.status_code == 404:
                raise LLMError(
                    f"{where} does not have model {self.model!r}. Pull it first: "
                    f"ollama pull {self.model}"
                ) from exc
            raise LLMError(f"{where} returned an error ({exc.status_code}): {exc.error}") from exc
        except ollama.RequestError as exc:
            raise LLMError(f"Ollama rejected the request: {exc}") from exc
        except (ConnectionError, OSError) as exc:
            raise LLMError(
                f"could not reach {where}: {exc}. Is `ollama serve` running, and is the host "
                "option (or OLLAMA_HOST) right?"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - the client raises transport errors of its HTTP library
            if type(exc).__module__.split(".")[0] in ("httpx", "httpx2", "httpcore"):
                raise LLMError(f"could not reach {where}: {exc}") from exc
            raise

        message = response.message
        text = (message.content or "") if message is not None else ""
        prompt_tokens = int(response.prompt_eval_count or 0)
        reply_tokens = int(response.eval_count or 0)
        finish = response.done_reason or "stop"
        if self.strict_context and prompt_tokens >= self.num_ctx:
            raise LLMError(
                f"the prompt filled the context window of {self.num_ctx} tokens, so Ollama cut "
                "it. Raise it with the num_ctx option (and make sure the model supports it), "
                "or set strict_context=false to accept cut prompts."
            )
        if not text.strip() and finish == "length":
            raise LLMError(
                f"{self.model} used its whole reply limit ({options['num_predict']} tokens) "
                "without producing any text. Raise max_output_tokens, or switch thinking off "
                "with think=false."
            )
        return LLMResponse(
            text=text,
            model=response.model or self.model,
            usage=Usage(input_tokens=prompt_tokens, output_tokens=reply_tokens),
            stop_reason={"stop": "end_turn", "length": "max_tokens"}.get(finish, finish),
            latency_s=time.time() - started,
            meta={
                "temperature": options.get("temperature"),
                "seed": options.get("seed"),
                "num_ctx": options["num_ctx"],
                "finish_reason": finish,
            },
        )
