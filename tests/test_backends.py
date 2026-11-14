"""Model and embedding backends: OpenAI-compatible servers, Ollama, Hugging Face.

The OpenAI-compatible and Ollama backends are driven, through their official client
libraries, against local stand-in servers that record what they are sent. The
Hugging Face backends load tiny models built on the spot with random weights, so
the libraries' own loading, templating, tokenising and generation code runs. None of
this says anything about how a real model behaves.
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pytest

from conftest import chat_payload, ollama_chat_payload
from self_evolving_agents.embeddings import make_embedder
from self_evolving_agents.llm import (
    LLMError,
    LLMRefusal,
    LLMRequest,
    TrackedLLM,
    is_stand_in,
    make_backend,
    parse_options,
    split_spec,
    user,
)


def request(text="hello", **kw):
    return LLMRequest(system="You are terse.", messages=[user(text)], max_tokens=300, **kw)


# --------------------------------------------------------------------------- descriptions


@pytest.mark.parametrize(
    "spec, expected",
    [
        ("anthropic:claude-opus-5-5", ("anthropic", "claude-opus-5-5", None)),
        ("ollama:llama3.2:3b", ("ollama", "llama3.2:3b", None)),
        (
            "ollama:llama3.2:3b@http://gpu-box:11434",
            ("ollama", "llama3.2:3b", "http://gpu-box:11434"),
        ),
        (
            "openai:Qwen/Qwen2.5-7B-Instruct@https://router.huggingface.co/v1",
            ("openai", "Qwen/Qwen2.5-7B-Instruct", "https://router.huggingface.co/v1"),
        ),
        ("openai:org@team/model", ("openai", "org@team/model", None)),
        (
            "huggingface:HuggingFaceTB/SmolLM2-1.7B-Instruct",
            ("hf", "HuggingFaceTB/SmolLM2-1.7B-Instruct", None),
        ),
        ("transformers:/models/local", ("hf", "/models/local", None)),
        ("offline-demo", ("offline-demo", "", None)),
    ],
)
def test_model_descriptions_are_split_into_provider_model_and_address(spec, expected):
    assert split_spec(spec) == expected


def test_options_are_read_as_json_where_possible():
    assert parse_options(["num_ctx=16384", "think=false", "device=cpu", "prefix=query: "]) == {
        "num_ctx": 16384,
        "think": False,
        "device": "cpu",
        "prefix": "query: ",
    }
    assert parse_options(['extra_body={"top_k": 20}']) == {"extra_body": {"top_k": 20}}
    with pytest.raises(ValueError, match="key=value"):
        parse_options(["num_ctx"])


def test_unknown_providers_and_options_are_reported_plainly():
    with pytest.raises(LLMError, match="provider must be one of"):
        make_backend("mystery:model")
    with pytest.raises(LLMError, match="num_ctx"):
        make_backend("openai:m@http://127.0.0.1:9/v1", num_ctx=1)  # an Ollama option
    assert is_stand_in("offline-demo") and not is_stand_in("ollama:llama3.2")


# --------------------------------------------------------------------------- OpenAI-compatible


def test_openai_backend_request_shape_and_reply(fake_openai):
    backend = make_backend(f"openai:local-model@{fake_openai.base_url}", seed=7)
    response = backend.complete(request("measure it", temperature=0.7, sample=2))
    sent = fake_openai.requests[-1]
    assert sent["path"] == "/v1/chat/completions"
    body = sent["body"]
    assert body["model"] == "local-model"
    assert body["messages"][0] == {"role": "system", "content": "You are terse."}
    assert body["messages"][1] == {"role": "user", "content": "measure it"}
    # The temperature is applied here (unlike on Claude), and the seed varies with the sample.
    assert body["temperature"] == 0.7 and body["seed"] == 9 and body["max_tokens"] == 300
    assert response.text.startswith("<think>")
    assert response.usage.input_tokens == 16 and response.usage.cache_read_tokens == 4
    assert response.usage.output_tokens == 5 and response.stop_reason == "end_turn"
    assert response.meta == {"temperature": 0.7, "seed": 9, "finish_reason": "stop"}


def test_openai_backend_options_change_the_request(fake_openai):
    backend = make_backend(
        f"openai:reasoner@{fake_openai.base_url}",
        honour_temperature=False,
        max_tokens_param="max_completion_tokens",
        max_output_tokens=100,
        reasoning_effort="low",
        extra_body={"top_k": 20},
    )
    backend.complete(request(temperature=0.0))
    body = fake_openai.requests[-1]["body"]
    assert "temperature" not in body and "max_tokens" not in body and "seed" not in body
    assert body["max_completion_tokens"] == 100 and body["reasoning_effort"] == "low"
    assert body["top_k"] == 20


def test_openai_backend_errors(fake_openai):
    backend = make_backend(f"openai:m@{fake_openai.base_url}", max_retries=0)
    fake_openai.responder = lambda body: (200, chat_payload("", refusal="I can't help with that"))
    with pytest.raises(LLMRefusal):
        backend.complete(request())
    fake_openai.responder = lambda body: (200, chat_payload("", finish="length"))
    with pytest.raises(LLMError, match="whole reply limit"):
        backend.complete(request())
    fake_openai.responder = lambda body: (
        400,
        {"error": {"message": "temperature is not supported", "type": "invalid_request_error"}},
    )
    with pytest.raises(LLMError, match="honour_temperature=false"):
        backend.complete(request(temperature=0.5))
    fake_openai.responder = lambda body: (
        404,
        {"error": {"message": "no such model", "type": "invalid_request_error"}},
    )
    with pytest.raises(LLMError, match="does not know model"):
        backend.complete(request())
    with pytest.raises(LLMError, match="could not reach"):
        make_backend("openai:m@http://127.0.0.1:9/v1", max_retries=0).complete(request())


def test_openai_backend_without_key_or_address_says_what_to_set(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    with pytest.raises(LLMError, match="OPENAI_API_KEY"):
        make_backend("openai:gpt-4o-mini")


def test_openai_embedder_restores_order_and_normalises(fake_openai):
    embedder = make_embedder(f"openai:embed-model@{fake_openai.base_url}", dimensions=3)
    vectors = embedder.embed(["a", "bbb", "cc"])
    body = fake_openai.requests[-1]["body"]
    assert body["input"] == ["a", "bbb", "cc"] and body["dimensions"] == 3
    assert vectors.shape == (3, 3)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)
    # The stand-in answers in reverse order; rows must still follow the input.
    raw = np.array([[1.0, 1.0, 0.0], [3.0, 1.0, 1.0], [2.0, 1.0, 2.0]])
    assert np.allclose(vectors, raw / np.linalg.norm(raw, axis=1, keepdims=True))


# --------------------------------------------------------------------------- Ollama


def test_ollama_backend_sets_context_and_reply_length(fake_ollama):
    backend = make_backend(
        f"ollama:llama3.2:3b@{fake_ollama.base_url}",
        num_ctx=4096,
        max_output_tokens=256,
        seed=3,
        think=False,
    )
    response = backend.complete(request("measure it", temperature=0.0, sample=1))
    sent = fake_ollama.requests[-1]
    assert sent["path"] == "/api/chat"
    body = sent["body"]
    assert body["model"] == "llama3.2:3b" and body["stream"] is False and body["think"] is False
    assert body["messages"][0] == {"role": "system", "content": "You are terse."}
    assert body["options"] == {"num_ctx": 4096, "num_predict": 256, "temperature": 0.0, "seed": 4}
    assert response.text.startswith("<think>") and response.usage.input_tokens == 20
    assert response.meta["num_ctx"] == 4096 and response.stop_reason == "end_turn"
    assert backend.price_per_mtok == (0.0, 0.0)


def test_ollama_backend_refuses_a_cut_prompt_and_reports_missing_models(fake_ollama):
    backend = make_backend(f"ollama:llama3.2:3b@{fake_ollama.base_url}", num_ctx=2048)
    fake_ollama.responder = lambda body: (200, ollama_chat_payload("ok", prompt_tokens=2048))
    with pytest.raises(LLMError, match="context window of 2048"):
        backend.complete(request())
    relaxed = make_backend(
        f"ollama:llama3.2:3b@{fake_ollama.base_url}", num_ctx=2048, strict_context=False
    )
    assert relaxed.complete(request()).text == "ok"
    with pytest.raises(LLMError, match="ollama pull missing-model"):
        make_backend(f"ollama:missing-model@{fake_ollama.base_url}").complete(request())
    with pytest.raises(LLMError, match="could not reach"):
        make_backend("ollama:llama3.2@http://127.0.0.1:9").complete(request())


def test_ollama_embedder(fake_ollama):
    embedder = make_embedder(f"ollama:nomic-embed-text@{fake_ollama.base_url}")
    vectors = embedder.embed(["a", "bbbb"])
    body = fake_ollama.requests[-1]["body"]
    assert fake_ollama.requests[-1]["path"] == "/api/embed"
    assert body["input"] == ["a", "bbbb"] and body["truncate"] is False
    assert vectors.shape == (2, 3) and np.allclose(np.linalg.norm(vectors, axis=1), 1.0)
    assert embedder.name == "ollama-nomic-embed-text"


# --------------------------------------------------------------------------- tracking


def test_applied_settings_are_part_of_the_cache_key(fake_openai, tmp_path):
    backend = make_backend(f"openai:m@{fake_openai.base_url}")
    llm = TrackedLLM(backend, cache_dir=tmp_path)
    llm.complete(request(temperature=0.0))
    llm.complete(request(temperature=0.0))
    assert len(fake_openai.requests) == 1, "the same request is answered from the cache"
    llm.complete(request(temperature=1.0))
    assert len(fake_openai.requests) == 2, "another temperature is another request"
    replay = TrackedLLM(make_backend(f"openai:m@{fake_openai.base_url}"), cache_dir=tmp_path)
    assert replay.complete(request(temperature=1.0)).meta["temperature"] == 1.0
    assert len(fake_openai.requests) == 2 and replay.cached_calls == 1


def test_costs_of_local_and_priced_backends(fake_openai, fake_ollama, tmp_path):
    local = TrackedLLM(make_backend(f"ollama:llama3.2@{fake_ollama.base_url}"))
    local.complete(request())
    assert local.summary()["estimated_cost_usd"] == 0.0
    priced = TrackedLLM(
        make_backend(f"openai:m@{fake_openai.base_url}", price_in=1.0, price_out=2.0)
    )
    priced.complete(request())
    # 16 uncached and 4 cached input tokens at $1 per million, 5 output tokens at $2.
    assert priced.cost_usd == pytest.approx((16 + 4 * 0.1 + 5 * 2.0) / 1e6)
    unpriced = TrackedLLM(make_backend(f"openai:m@{fake_openai.base_url}"))
    unpriced.complete(request())
    assert unpriced.summary()["estimated_cost_usd"] is None


# --------------------------------------------------------------------------- Hugging Face


class FakeRunner:
    context_length = 50

    def __init__(self):
        self.calls = []

    def render(self, messages):
        return " | ".join(f"{m['role']}: {m['content']}" for m in messages) + " | assistant:"

    def count(self, prompt):
        return len(prompt.split())

    def generate(self, prompt, *, max_new_tokens, temperature, seed):
        self.calls.append(
            {"max_new_tokens": max_new_tokens, "temperature": temperature, "seed": seed}
        )
        return f"reply {seed}", 2, "stop"


def test_huggingface_backend_logic_with_a_stand_in_runner():
    from self_evolving_agents.llm.huggingface_backend import HuggingFaceBackend

    runner = FakeRunner()
    backend = HuggingFaceBackend("local/model", runner=runner, seed=10, max_output_tokens=30)
    response = backend.complete(request("measure it", sample=2))
    assert response.text == "reply 12" and response.usage.input_tokens == 10
    # The reply limit is the smallest of: the request's, the backend's, what is left of the window.
    assert runner.calls[-1] == {"max_new_tokens": 30, "temperature": None, "seed": 12}
    backend.complete(request("measure it " * 10, temperature=0.8))
    assert runner.calls[-1]["max_new_tokens"] == 50 - 28 and runner.calls[-1]["temperature"] == 0.8
    with pytest.raises(LLMError, match="context window is 50"):
        backend.complete(request("word " * 60))


@pytest.mark.filterwarnings("ignore")
def test_huggingface_backend_runs_a_real_transformers_model(tiny_hf_models, tmp_path):
    backend = make_backend(f"hf:{tiny_hf_models['chat']}", device="cpu", max_output_tokens=6)
    greedy = request("measure the sample")
    first, second = backend.complete(greedy), backend.complete(greedy)
    assert first.text == second.text, "greedy decoding repeats"
    assert first.usage.output_tokens == 6 and first.usage.input_tokens > 5
    assert first.meta["temperature"] is None
    hot = [
        backend.complete(request("measure the sample", temperature=1.5, sample=i)).text
        for i in range(4)
    ]
    again = [
        backend.complete(request("measure the sample", temperature=1.5, sample=i)).text
        for i in range(4)
    ]
    assert hot == again, "a seeded sample repeats"
    assert len(set(hot)) > 1, "different sample indices give different draws"
    with pytest.raises(LLMError, match="context window is 64"):
        backend.complete(request("scan " * 80))
    # Through the tracking wrapper, the cost of a local model is zero.
    tracked = TrackedLLM(backend, cache_dir=tmp_path)
    tracked.complete(greedy)
    assert tracked.summary()["estimated_cost_usd"] == 0.0


@pytest.mark.filterwarnings("ignore")
def test_huggingface_embedder_runs_a_real_sentence_transformers_model(tiny_hf_models, tmp_path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        embedder = make_embedder(
            f"hf:{tiny_hf_models['encoder']}", cache_dir=tmp_path, device="cpu"
        )
        vectors = embedder.embed(["the agent scans", "measure the sample", "the agent scans"])
    assert vectors.shape == (3, 16)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)
    assert np.allclose(vectors[0], vectors[2]) and not np.allclose(vectors[0], vectors[1])
    cached = [json.loads(line) for line in (tmp_path / "embeddings.jsonl").read_text().splitlines()]
    assert len(cached) == 2, "each distinct text is embedded once and kept on disk"
