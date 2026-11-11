"""Deterministic stand-in for a language model.

This is a test double. It lets the whole pipeline be exercised offline and for
free, but nothing it produces says anything about how a real model would behave.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import LLMError, LLMRequest, LLMResponse, Usage

Handler = Callable[[LLMRequest], str]


class ScriptedLLM:
    """Answers requests from a script keyed by ``request.purpose``.

    Each entry may be a fixed string, a list of strings consumed in order, or a
    function of the request. ``"*"`` is the fallback entry. A bare callable handles
    every purpose.
    """

    def __init__(
        self,
        script: Handler | dict[str, Handler | list[str] | str],
        model: str = "scripted",
    ):
        self.model = model
        self._script = script
        self.requests: list[LLMRequest] = []

    def _answer(self, request: LLMRequest) -> str:
        if callable(self._script):
            return self._script(request)
        entry = self._script.get(request.purpose, self._script.get("*"))
        if entry is None:
            raise LLMError(f"ScriptedLLM has no entry for purpose {request.purpose!r}")
        if callable(entry):
            return entry(request)
        if isinstance(entry, list):
            if not entry:
                raise LLMError(f"ScriptedLLM ran out of responses for {request.purpose!r}")
            return entry.pop(0)
        return entry

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        text = self._answer(request)
        prompt_chars = len(request.system) + sum(len(m["content"]) for m in request.messages)
        return LLMResponse(
            text=text,
            model=self.model,
            # Character counts stand in for tokens so that accounting code has numbers to add.
            usage=Usage(input_tokens=prompt_chars // 4, output_tokens=len(text) // 4),
        )

    def purposes(self) -> list[str]:
        return [r.purpose for r in self.requests]
