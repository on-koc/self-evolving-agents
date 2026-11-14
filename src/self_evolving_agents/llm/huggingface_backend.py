"""Models run on the local machine with Hugging Face ``transformers``.

The model is loaded once and kept in memory. Each request is rendered with the
model's own chat template, generated from, and decoded. A fixed seed plus the
request's sample index is set before every generation, so a run repeats exactly on
the same hardware and library versions.

The class is split in two so that its logic can be tested without downloading a
model: :class:`HuggingFaceBackend` turns a request into a prompt and settings, and a
*runner* does the tokenising and generating. The default runner uses
``transformers`` and ``torch``.

Hosted Hugging Face inference is a different thing: it speaks the OpenAI protocol,
so use ``openai:<model>@https://router.huggingface.co/v1`` for it.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from .base import LLMError, LLMRequest, LLMResponse, Usage


class Runner(Protocol):
    """What the backend needs from a loaded model."""

    context_length: int | None

    def render(self, messages: list[dict[str, str]]) -> str:
        """The prompt text for a conversation, ending where the model's reply begins."""

    def count(self, prompt: str) -> int:
        """Number of tokens in the prompt."""

    def generate(
        self, prompt: str, *, max_new_tokens: int, temperature: float | None, seed: int
    ) -> tuple[str, int, str]:
        """``(reply text, tokens generated, "stop" or "length")``."""


class TransformersRunner:
    """Loads a causal language model and its tokenizer with ``transformers``."""

    def __init__(
        self,
        model: str,
        *,
        device: str = "auto",
        dtype: str = "auto",
        revision: str | None = None,
        trust_remote_code: bool = False,
        chat_template_kwargs: dict[str, Any] | None = None,
        top_p: float | None = None,
    ):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise LLMError(
                "The Hugging Face backend needs transformers and torch: "
                "pip install 'self-evolving-agents[huggingface]'"
            ) from exc
        self._torch = torch
        self.chat_template_kwargs = dict(chat_template_kwargs or {})
        self.top_p = top_p
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model, revision=revision, trust_remote_code=trust_remote_code
            )
            kwargs: dict[str, Any] = {"revision": revision, "trust_remote_code": trust_remote_code}
            if dtype != "auto":
                kwargs["dtype"] = getattr(torch, dtype)
            self.lm = AutoModelForCausalLM.from_pretrained(model, **kwargs)
        except OSError as exc:
            raise LLMError(
                f"could not load {model!r} with transformers: {exc}. Check the name, the "
                "revision, and that the files can be downloaded (or are in the local cache)."
            ) from exc
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
            mps = getattr(torch.backends, "mps", None)
            if device == "cpu" and mps is not None and mps.is_available():
                device = "mps"
        self.device = device
        self.lm.to(device)
        self.lm.eval()
        limit = getattr(self.lm.config, "max_position_embeddings", None) or getattr(
            self.lm.config, "n_positions", None
        )
        self.context_length = int(limit) if limit else None

    def render(self, messages: list[dict[str, str]]) -> str:
        if not getattr(self.tokenizer, "chat_template", None):
            raise LLMError(
                "this model's tokenizer has no chat template, so a conversation cannot be "
                "rendered for it. Use an instruction-tuned (chat) model."
            )
        try:
            return self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, **self.chat_template_kwargs
            )
        except Exception as exc:  # noqa: BLE001 - templates raise their own error types
            if messages and messages[0]["role"] == "system":
                # Some templates accept no system turn: fold it into the first user turn.
                system, rest = messages[0]["content"], [dict(m) for m in messages[1:]]
                if rest and rest[0]["role"] == "user":
                    rest[0]["content"] = system + "\n\n" + rest[0]["content"]
                    return self.tokenizer.apply_chat_template(
                        rest,
                        tokenize=False,
                        add_generation_prompt=True,
                        **self.chat_template_kwargs,
                    )
            raise LLMError(f"the model's chat template rejected the conversation: {exc}") from exc

    def _encode(self, prompt: str) -> Any:
        # The template already wrote the special tokens it wants.
        return self.tokenizer(prompt, return_tensors="pt", add_special_tokens=False)

    def count(self, prompt: str) -> int:
        return int(self._encode(prompt)["input_ids"].shape[1])

    def generate(
        self, prompt: str, *, max_new_tokens: int, temperature: float | None, seed: int
    ) -> tuple[str, int, str]:
        torch = self._torch
        inputs = self._encode(prompt).to(self.device)
        sample = temperature is not None and temperature > 0
        kwargs: dict[str, Any] = {"max_new_tokens": max_new_tokens, "do_sample": sample}
        if sample:
            kwargs["temperature"] = float(temperature)
            if self.top_p is not None:
                kwargs["top_p"] = float(self.top_p)
        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
            kwargs["pad_token_id"] = self.tokenizer.eos_token_id
        torch.manual_seed(seed)
        if self.device.startswith("cuda"):
            torch.cuda.manual_seed_all(seed)
        with torch.no_grad():
            output = self.lm.generate(**inputs, **kwargs)
        new_tokens = output[0][inputs["input_ids"].shape[1] :]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        ended = self.tokenizer.eos_token_id is not None and bool(
            (new_tokens == self.tokenizer.eos_token_id).any()
        )
        finish = "stop" if ended or len(new_tokens) < max_new_tokens else "length"
        return text, int(len(new_tokens)), finish


class HuggingFaceBackend:
    """Answers :class:`LLMRequest` objects with a model run by ``transformers``.

    Args:
        model: a model id on the Hugging Face Hub or a local directory.
        device: ``auto`` (GPU if there is one), ``cpu``, ``cuda``, ``cuda:1``, ``mps``.
        dtype: ``auto`` or a torch type name such as ``float16`` or ``bfloat16``.
        revision: a commit of the model repository. Pin it for a run that has to be
            repeatable; a model id alone can change under you.
        seed: base of the generation seed; the request's sample index is added.
        max_output_tokens: upper limit on the reply length.
        default_temperature: used when a request names none. ``None`` means greedy
            decoding, which is the repeatable choice.
        chat_template_kwargs: extra arguments for the chat template (for example
            ``{"enable_thinking": false}`` for models that have the switch).
        runner: an object with ``render``, ``count`` and ``generate`` (used by tests).
    """

    price_per_mtok = (0.0, 0.0)

    def __init__(
        self,
        model: str,
        *,
        device: str = "auto",
        dtype: str = "auto",
        revision: str | None = None,
        seed: int = 0,
        max_output_tokens: int = 2048,
        default_temperature: float | None = None,
        top_p: float | None = None,
        trust_remote_code: bool = False,
        chat_template_kwargs: dict[str, Any] | None = None,
        runner: Runner | None = None,
    ):
        if not model:
            raise LLMError("a Hugging Face backend needs a model name: hf:<model>")
        self.model = model
        self.revision = revision
        self.seed = int(seed)
        self.max_output_tokens = int(max_output_tokens)
        self.default_temperature = default_temperature
        self.runner: Runner = runner or TransformersRunner(
            model,
            device=device,
            dtype=dtype,
            revision=revision,
            trust_remote_code=trust_remote_code,
            chat_template_kwargs=chat_template_kwargs,
            top_p=top_p,
        )

    def _temperature(self, request: LLMRequest) -> float | None:
        return self.default_temperature if request.temperature is None else request.temperature

    def signature(self, request: LLMRequest) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "temperature": self._temperature(request),
            "seed": self.seed + int(request.sample),
        }

    def complete(self, request: LLMRequest) -> LLMResponse:
        messages = [{"role": m["role"], "content": m["content"]} for m in request.messages]
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        started = time.time()
        prompt = self.runner.render(messages)
        prompt_tokens = self.runner.count(prompt)
        limit = min(int(request.max_tokens), self.max_output_tokens)
        window = self.runner.context_length
        if window is not None and prompt_tokens + 1 > window:
            raise LLMError(
                f"the prompt has {prompt_tokens} tokens and the model's context window is "
                f"{window}. Nothing was generated: a cut prompt would give a meaningless reply."
            )
        if window is not None:
            limit = min(limit, window - prompt_tokens)
        temperature = self._temperature(request)
        seed = self.seed + int(request.sample)
        text, reply_tokens, finish = self.runner.generate(
            prompt, max_new_tokens=limit, temperature=temperature, seed=seed
        )
        if not text.strip() and finish == "length":
            raise LLMError(
                f"{self.model} used its whole reply limit ({limit} tokens) without producing "
                "any text. Raise max_output_tokens."
            )
        return LLMResponse(
            text=text,
            model=self.model,
            usage=Usage(input_tokens=prompt_tokens, output_tokens=reply_tokens),
            stop_reason={"stop": "end_turn", "length": "max_tokens"}.get(finish, finish),
            latency_s=time.time() - started,
            meta={"temperature": temperature, "seed": seed, "finish_reason": finish},
        )
