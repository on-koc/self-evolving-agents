"""Provider-neutral LLM interface plus the tracking wrapper every call goes through.

A backend only has to turn an :class:`LLMRequest` into text. Caching, spend limits
and provenance logging are layered on by :class:`TrackedLLM`, so they behave the
same for every backend, including the offline doubles.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ..types import new_id, stable_hash

if TYPE_CHECKING:
    from ..provenance import ProvenanceStore


class LLMError(RuntimeError):
    """A call failed in a way retrying will not fix."""


class LLMRefusal(LLMError):
    """The model declined to answer (``stop_reason == "refusal"``)."""


class BudgetExceeded(LLMError):
    """The configured spend, call or token limit has been reached."""


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Usage:
        return cls(**{k: int(d.get(k, 0) or 0) for k in cls().to_dict()})


@dataclass
class LLMRequest:
    """One completion request.

    ``purpose`` names the role of the call (``act``, ``judge``, ``extract``, ...) and is
    used for accounting and by scripted backends. ``sample`` distinguishes repeated
    draws of an otherwise identical prompt, so that test-time scaling can ask for
    several different rollouts and still be replayed from the cache.

    ``temperature`` is a hint. Backends whose API no longer accepts sampling
    parameters (current Claude models) ignore it.
    """

    system: str
    messages: list[dict[str, str]]
    purpose: str = "generic"
    max_tokens: int = 16000
    temperature: float | None = None
    sample: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def cache_key(self, model: str) -> str:
        return stable_hash(
            {
                "model": model,
                "system": self.system,
                "messages": self.messages,
                "max_tokens": self.max_tokens,
                "sample": self.sample,
            },
            length=32,
        )


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: Usage = field(default_factory=Usage)
    stop_reason: str = "end_turn"
    latency_s: float = 0.0
    cached: bool = False
    call_id: str = ""


@runtime_checkable
class LLMBackend(Protocol):
    """Anything that can answer an :class:`LLMRequest`."""

    model: str

    def complete(self, request: LLMRequest) -> LLMResponse: ...


# USD per million tokens (input, output). Used only for the local spend estimate;
# the provider's invoice is authoritative. Unknown models are counted in tokens only.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-fable-5-2": (8.00, 40.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.00, 5.00),
}


def estimate_cost_usd(model: str, usage: Usage) -> float | None:
    """Rough cost of one call, or ``None`` if the model's prices are not known here.

    Cache reads are billed at about a tenth of the input price and cache writes at
    about 1.25x; both are approximations of the published multipliers.
    """
    price = PRICES_PER_MTOK.get(model)
    if price is None:
        return None
    p_in, p_out = price
    return (
        usage.input_tokens * p_in
        + usage.cache_read_tokens * p_in * 0.1
        + usage.cache_write_tokens * p_in * 1.25
        + usage.output_tokens * p_out
    ) / 1e6


@dataclass
class Budget:
    """Hard limits for a run. ``None`` means unlimited."""

    max_cost_usd: float | None = None
    max_calls: int | None = None
    max_output_tokens: int | None = None


class TrackedLLM:
    """Wraps a backend with a disk cache, a budget guard and provenance logging.

    Cached responses cost nothing and do not count against the budget, which makes
    interrupted runs resumable: rerun the same command and only the missing calls
    are paid for.
    """

    def __init__(
        self,
        backend: LLMBackend,
        *,
        cache_dir: str | Path | None = None,
        budget: Budget | None = None,
        store: ProvenanceStore | None = None,
    ):
        self.backend = backend
        self.model = backend.model
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.budget = budget or Budget()
        self.store = store
        self.calls = 0
        self.cached_calls = 0
        self.usage = Usage()
        self.cost_usd = 0.0
        self.cost_known = True

    # -- cache ------------------------------------------------------------------

    def _cache_path(self, key: str) -> Path | None:
        return self.cache_dir / f"{key}.json" if self.cache_dir else None

    def _cache_get(self, key: str) -> LLMResponse | None:
        path = self._cache_path(key)
        if path is None or not path.exists():
            return None
        try:
            d = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        return LLMResponse(
            text=d["text"],
            model=d.get("model", self.model),
            usage=Usage.from_dict(d.get("usage", {})),
            stop_reason=d.get("stop_reason", "end_turn"),
            latency_s=0.0,
            cached=True,
        )

    def _cache_put(self, key: str, request: LLMRequest, response: LLMResponse) -> None:
        path = self._cache_path(key)
        if path is None:
            return
        payload = {
            "text": response.text,
            "model": response.model,
            "usage": response.usage.to_dict(),
            "stop_reason": response.stop_reason,
            "purpose": request.purpose,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        tmp.replace(path)

    # -- budget -----------------------------------------------------------------

    def _check_budget(self) -> None:
        b = self.budget
        paid_calls = self.calls - self.cached_calls
        if b.max_calls is not None and paid_calls >= b.max_calls:
            raise BudgetExceeded(f"call limit reached ({b.max_calls})")
        if b.max_output_tokens is not None and self.usage.output_tokens >= b.max_output_tokens:
            raise BudgetExceeded(f"output token limit reached ({b.max_output_tokens})")
        if b.max_cost_usd is not None:
            if not self.cost_known:
                raise BudgetExceeded(
                    f"a cost limit is set but prices for model {self.model!r} are unknown; "
                    "use max_calls or max_output_tokens instead"
                )
            if self.cost_usd >= b.max_cost_usd:
                raise BudgetExceeded(
                    f"cost limit reached (${self.cost_usd:.2f} of ${b.max_cost_usd:.2f})"
                )

    # -- main entry point -------------------------------------------------------

    def complete(self, request: LLMRequest) -> LLMResponse:
        key = request.cache_key(self.model)
        response = self._cache_get(key)
        if response is None:
            self._check_budget()
            started = time.time()
            response = self.backend.complete(request)
            response.latency_s = response.latency_s or (time.time() - started)
            self._cache_put(key, request, response)
            self.usage.input_tokens += response.usage.input_tokens
            self.usage.output_tokens += response.usage.output_tokens
            self.usage.cache_read_tokens += response.usage.cache_read_tokens
            self.usage.cache_write_tokens += response.usage.cache_write_tokens
            cost = estimate_cost_usd(response.model, response.usage)
            if cost is None:
                self.cost_known = False
            else:
                self.cost_usd += cost
        else:
            self.cached_calls += 1
        self.calls += 1
        response.call_id = new_id("llm")
        if self.store is not None:
            self.store.record_llm_call(
                response.call_id,
                purpose=request.purpose,
                model=response.model,
                request={
                    "system": request.system,
                    "messages": request.messages,
                    "sample": request.sample,
                    "meta": request.meta,
                },
                response=response.text,
                usage=response.usage.to_dict(),
                latency_s=response.latency_s,
                cached=response.cached,
            )
        return response

    def summary(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "calls": self.calls,
            "cached_calls": self.cached_calls,
            "usage": self.usage.to_dict(),
            "estimated_cost_usd": round(self.cost_usd, 4) if self.cost_known else None,
        }


def user(text: str) -> dict[str, str]:
    return {"role": "user", "content": text}


def assistant(text: str) -> dict[str, str]:
    return {"role": "assistant", "content": text}
