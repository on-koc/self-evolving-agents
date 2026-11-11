"""The LLM layer: tracking wrapper, scripted double, and the Claude backend's request shape.

The Claude backend is exercised through the real ``anthropic`` SDK against a local
fake server. That checks what this code sends and how it reads replies; it does not
prove that the live API accepts the request.
"""

from __future__ import annotations

import pytest

from conftest import message_payload, requires_anthropic
from self_evolving_agents.llm import (
    Budget,
    BudgetExceeded,
    LLMError,
    LLMRefusal,
    LLMRequest,
    ScriptedLLM,
    TrackedLLM,
    Usage,
    estimate_cost_usd,
    make_backend,
    user,
)
from self_evolving_agents.provenance import ProvenanceStore


def request(text="hi", **kw):
    return LLMRequest(system="sys", messages=[user(text)], **kw)


# --------------------------------------------------------------------------- scripted


def test_scripted_dispatches_by_purpose():
    llm = ScriptedLLM(
        {
            "act": ["first", "second"],
            "judge": lambda r: r.messages[0]["content"].upper(),
            "*": "other",
        }
    )
    assert llm.complete(request(purpose="act")).text == "first"
    assert llm.complete(request(purpose="act")).text == "second"
    assert llm.complete(request("abc", purpose="judge")).text == "ABC"
    assert llm.complete(request(purpose="anything")).text == "other"
    assert llm.purposes() == ["act", "act", "judge", "anything"]
    with pytest.raises(LLMError, match="ran out"):
        llm.complete(request(purpose="act"))


def test_scripted_without_fallback_names_the_missing_purpose():
    with pytest.raises(LLMError, match="extract"):
        ScriptedLLM({"act": "x"}).complete(request(purpose="extract"))


# --------------------------------------------------------------------------- tracking


def test_cache_replays_without_calling_the_backend(tmp_path):
    backend = ScriptedLLM(lambda r: f"reply {len(backend.requests)}")
    llm = TrackedLLM(backend, cache_dir=tmp_path)
    first = llm.complete(request())
    second = llm.complete(request())
    assert (first.text, first.cached) == ("reply 1", False)
    assert (second.text, second.cached) == ("reply 1", True)
    assert len(backend.requests) == 1
    assert llm.summary()["calls"] == 2 and llm.summary()["cached_calls"] == 1
    assert first.call_id != second.call_id, "every use gets its own id, cached or not"

    fresh = TrackedLLM(ScriptedLLM("never used"), cache_dir=tmp_path)
    assert fresh.complete(request()).text == "reply 1", "the cache survives a restart"


def test_cache_key_separates_samples_but_not_purposes(tmp_path):
    backend = ScriptedLLM(lambda r: f"reply {len(backend.requests)}")
    llm = TrackedLLM(backend, cache_dir=tmp_path)
    a = llm.complete(request(sample=0))
    b = llm.complete(request(sample=1))
    c = llm.complete(request(sample=0, purpose="different-label"))
    assert a.text != b.text, "different samples are different draws"
    assert c.text == a.text and c.cached


def test_budget_limits_paid_calls_only(tmp_path):
    llm = TrackedLLM(ScriptedLLM("ok"), cache_dir=tmp_path, budget=Budget(max_calls=2))
    llm.complete(request("a"))
    llm.complete(request("b"))
    llm.complete(request("a"))  # cached: free
    with pytest.raises(BudgetExceeded, match="call limit"):
        llm.complete(request("c"))


def test_budget_on_output_tokens():
    llm = TrackedLLM(ScriptedLLM("x" * 400), budget=Budget(max_output_tokens=150))
    llm.complete(request("a"))
    llm.complete(request("b"))
    with pytest.raises(BudgetExceeded, match="output token"):
        llm.complete(request("c"))


def test_cost_budget_needs_known_prices():
    class Priced:
        model = "claude-haiku-5-5"

        def complete(self, r):
            from self_evolving_agents.llm import LLMResponse

            return LLMResponse("ok", self.model, Usage(input_tokens=1_000_000, output_tokens=0))

    llm = TrackedLLM(Priced(), budget=Budget(max_cost_usd=0.15))
    llm.complete(request("a"))
    assert llm.cost_usd == pytest.approx(0.10)
    llm.complete(request("b"))
    with pytest.raises(BudgetExceeded, match="cost limit"):
        llm.complete(request("c"))

    unknown = TrackedLLM(ScriptedLLM("ok", model="mystery"), budget=Budget(max_cost_usd=1.0))
    unknown.complete(request("a"))
    assert unknown.summary()["estimated_cost_usd"] is None
    with pytest.raises(BudgetExceeded, match="prices"):
        unknown.complete(request("b"))


def test_estimate_cost_counts_cache_tokens():
    usage = Usage(
        input_tokens=1000, output_tokens=1000, cache_read_tokens=1000, cache_write_tokens=1000
    )
    assert estimate_cost_usd("claude-opus-5-5", usage) == pytest.approx(
        (1000 * 4 + 1000 * 0.4 + 1000 * 5 + 1000 * 20) / 1e6
    )
    assert estimate_cost_usd("not-a-model", usage) is None


def test_calls_are_logged_to_provenance():
    store = ProvenanceStore()
    llm = TrackedLLM(ScriptedLLM("answer"), store=store)
    response = llm.complete(request(purpose="judge", meta={"trajectory": "t1"}))
    logged = store.get_llm_call(response.call_id)
    assert logged["purpose"] == "judge" and logged["response"] == "answer"
    assert logged["request"]["meta"] == {"trajectory": "t1"}
    assert store.get_node(response.call_id)["prov_type"] == "activity"


def test_make_backend_specs():
    assert make_backend("offline-demo").model == "offline-demo"
    with pytest.raises(LLMError, match="unknown LLM spec"):
        make_backend("gpt-oops")


# --------------------------------------------------------------------------- Claude backend


def backend_for(server, model, **kw):
    import anthropic

    from self_evolving_agents.llm.anthropic_backend import AnthropicBackend

    client = anthropic.Anthropic(api_key="test-key", base_url=server.base_url, max_retries=0)
    return AnthropicBackend(model, client=client, **kw)


@requires_anthropic
def test_claude_request_shape_and_reply_parsing(fake_anthropic):
    backend = backend_for(fake_anthropic, "claude-haiku-5-5", effort="low")
    response = backend.complete(
        LLMRequest(
            system="You are a test.", messages=[user("hello")], temperature=0.0, max_tokens=321
        )
    )
    sent = fake_anthropic.requests[-1]
    body = sent["body"]

    assert sent["path"].startswith("/v1/messages")
    assert body["model"] == "claude-haiku-5-5" and body["max_tokens"] == 321
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    assert body["system"] == [
        {"type": "text", "text": "You are a test.", "cache_control": {"type": "ephemeral"}}
    ]
    assert body["output_config"] == {"effort": "low"}
    for removed in ("temperature", "top_p", "top_k", "thinking", "fallbacks"):
        assert removed not in body, f"{removed} must not be sent"

    assert response.text == "hello", "thinking blocks are skipped; only text is returned"
    assert response.usage == Usage(12, 5, cache_read_tokens=3, cache_write_tokens=2)
    assert response.stop_reason == "end_turn"


@requires_anthropic
def test_claude_requests_refusal_fallback_only_where_supported(fake_anthropic):
    backend_for(fake_anthropic, "claude-opus-5-5").complete(request())
    sent = fake_anthropic.requests[-1]
    assert sent["body"]["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in sent["headers"].get("anthropic-beta", "")

    backend_for(fake_anthropic, "claude-opus-5-5", refusal_fallback=False).complete(request())
    assert "fallbacks" not in fake_anthropic.requests[-1]["body"]

    backend_for(fake_anthropic, "claude-haiku-5-5").complete(request())
    assert "fallbacks" not in fake_anthropic.requests[-1]["body"]


@requires_anthropic
def test_claude_omits_optional_blocks(fake_anthropic):
    backend = backend_for(fake_anthropic, "claude-haiku-5-5", cache_system_prompt=False)
    backend.complete(LLMRequest(system="", messages=[user("x")]))
    body = fake_anthropic.requests[-1]["body"]
    assert "system" not in body and "output_config" not in body

    backend.complete(LLMRequest(system="plain", messages=[user("x")]))
    assert fake_anthropic.requests[-1]["body"]["system"] == [{"type": "text", "text": "plain"}]


@requires_anthropic
def test_claude_refusal_raises(fake_anthropic):
    fake_anthropic.responder = lambda body: (
        200,
        message_payload(
            text="",
            stop_reason="refusal",
            stop_details={"type": "refusal", "category": "bio", "explanation": "declined"},
        ),
    )
    with pytest.raises(LLMRefusal, match="bio"):
        backend_for(fake_anthropic, "claude-haiku-5-5").complete(request())


@requires_anthropic
@pytest.mark.parametrize(
    "status, kind, match",
    [
        (401, "authentication_error", "credentials"),
        (404, "not_found_error", "Unknown model"),
        (400, "invalid_request_error", "rejected the request"),
        (529, "overloaded_error", "API error 529"),
    ],
)
def test_claude_errors_become_llm_errors(fake_anthropic, status, kind, match):
    fake_anthropic.responder = lambda body: (
        status,
        {"type": "error", "error": {"type": kind, "message": "nope"}},
    )
    with pytest.raises(LLMError, match=match):
        backend_for(fake_anthropic, "claude-haiku-5-5").complete(request())


@requires_anthropic
def test_claude_backend_works_under_tracking(fake_anthropic, tmp_path):
    llm = TrackedLLM(backend_for(fake_anthropic, "claude-haiku-5-5"), cache_dir=tmp_path)
    llm.complete(request())
    llm.complete(request())
    assert len(fake_anthropic.requests) == 1
    assert llm.summary()["usage"]["input_tokens"] == 12
    assert llm.summary()["estimated_cost_usd"] is not None
