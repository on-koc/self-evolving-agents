"""Shared fixtures. Nothing here talks to a real language model."""

from __future__ import annotations

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from self_evolving_agents.llm import ScriptedLLM

HAS_BSK = (
    importlib.util.find_spec("bsk_rl") is not None
    and importlib.util.find_spec("Basilisk") is not None
)
HAS_DW = importlib.util.find_spec("discoveryworld") is not None
HAS_ANTHROPIC = importlib.util.find_spec("anthropic") is not None

requires_bsk = pytest.mark.skipif(not HAS_BSK, reason="Basilisk / BSK-RL not installed")
requires_dw = pytest.mark.skipif(not HAS_DW, reason="discoveryworld not installed")
requires_anthropic = pytest.mark.skipif(not HAS_ANTHROPIC, reason="anthropic SDK not installed")


ITEM = """# Memory Item 1
## Title Keep a reserve
## Description Use when the battery can run flat.
## Content Charge before the battery gets low (rule: charge_below=0.35)."""


@pytest.fixture
def scripted():
    """A scripted model that scans, judges by the word 'lost', and extracts one canned item."""

    def judge(request):
        lost = "spacecraft lost" in request.messages[0]["content"]
        return f'Thoughts: looked at the ending.\nStatus: "{"failure" if lost else "success"}"'

    return ScriptedLLM(
        {
            "act": "<think>collect data</think><action>scan</action>",
            "judge": judge,
            "extract": ITEM,
            "refine": "- charge earlier",
            "select": '```\n{"index": [1], "analysis": "compared them"}\n```',
        }
    )


class _FakeAnthropic(BaseHTTPRequestHandler):
    """Minimal stand-in for the Messages endpoint that records what it was sent."""

    def log_message(self, *args):  # silence the default stderr logging
        pass

    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        server = self.server
        server.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
        status, payload = server.responder(body)
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.send_header("request-id", "req_test")
        self.end_headers()
        self.wfile.write(data)


def message_payload(text="hello", stop_reason="end_turn", model="claude-opus-5-5", **extra):
    payload = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "text", "text": text},
        ],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": 12,
            "output_tokens": 5,
            "cache_read_input_tokens": 3,
            "cache_creation_input_tokens": 2,
        },
    }
    payload.update(extra)
    return payload


@pytest.fixture
def fake_anthropic():
    """A local HTTP server speaking just enough of the Messages API for the real SDK."""
    server = HTTPServer(("127.0.0.1", 0), _FakeAnthropic)
    server.requests = []
    server.responder = lambda body: (200, message_payload())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def tmp_run(tmp_path: Path) -> Path:
    return tmp_path


class _FakeGemini(BaseHTTPRequestHandler):
    """Minimal stand-in for the Gemini batch-embedding endpoint."""

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        self.server.requests.append((self.path, body))
        count = len(body.get("requests", [])) or 1
        payload = {"embeddings": [{"values": [0.1 * (i + 1), 0.2, 0.3]} for i in range(count)]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def fake_gemini():
    """A local HTTP server that answers the official Google SDK's embedding request."""
    pytest.importorskip("google.genai")
    server = HTTPServer(("127.0.0.1", 0), _FakeGemini)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


# --------------------------------------------------------------------------- OpenAI-compatible


def chat_payload(text="hello", finish="stop", model="local-model", cached=4, refusal=None):
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text, "refusal": refusal},
                "finish_reason": finish,
                "logprobs": None,
            }
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 5,
            "total_tokens": 25,
            "prompt_tokens_details": {"cached_tokens": cached},
        },
    }


def scripted_reply(messages):
    """What a stand-in server says to the prompts of the stream methods (act, judge, extract)."""
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    if '"success" or "failure"' in system:  # the judge's answer format
        return 'Thoughts: looked at the end.\nStatus: "success"'
    if (
        "# Memory Item i\n" in system
    ):  # the extractor's output format (retrieved items are numbered)
        return ITEM
    return "<think>collect data</think><action>scan</action>"


class _FakeOpenAI(BaseHTTPRequestHandler):
    """Minimal stand-in for /v1/chat/completions and /v1/embeddings."""

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        server = self.server
        server.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
        if self.path.endswith("/embeddings"):
            texts = body["input"] if isinstance(body["input"], list) else [body["input"]]
            # Returned in reverse order, with indices, as the protocol allows.
            data = [
                {"object": "embedding", "index": i, "embedding": [float(len(t)), 1.0, float(i)]}
                for i, t in enumerate(texts)
            ][::-1]
            status, payload = 200, {"object": "list", "data": data, "model": body["model"]}
        else:
            status, payload = server.responder(body)
        out = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


@pytest.fixture
def fake_openai():
    """A local HTTP server speaking enough of the OpenAI protocol for the official SDK."""
    pytest.importorskip("openai")
    server = HTTPServer(("127.0.0.1", 0), _FakeOpenAI)
    server.requests = []
    server.responder = lambda body: (200, chat_payload(scripted_reply(body["messages"])))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.base_url = f"http://127.0.0.1:{server.server_port}/v1"
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


# --------------------------------------------------------------------------- Ollama


def ollama_chat_payload(text="hello", prompt_tokens=20, finish="stop", model="llama3.2:3b"):
    return {
        "model": model,
        "created_at": "2026-01-01T00:00:00Z",
        "message": {"role": "assistant", "content": text},
        "done": True,
        "done_reason": finish,
        "total_duration": 1,
        "load_duration": 1,
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": 1,
        "eval_count": 5,
        "eval_duration": 1,
    }


class _FakeOllama(BaseHTTPRequestHandler):
    """Minimal stand-in for Ollama's /api/chat and /api/embed."""

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        server = self.server
        server.requests.append({"path": self.path, "body": body})
        if body.get("model") == "missing-model":
            status, payload = 404, {"error": "model 'missing-model' not found"}
        elif self.path == "/api/embed":
            texts = body["input"] if isinstance(body["input"], list) else [body["input"]]
            status, payload = (
                200,
                {"model": body["model"], "embeddings": [[float(len(t)), 2.0, 0.0] for t in texts]},
            )
        else:
            status, payload = server.responder(body)
        out = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


@pytest.fixture
def fake_ollama():
    """A local HTTP server speaking enough of Ollama's API for the official client."""
    pytest.importorskip("ollama")
    server = HTTPServer(("127.0.0.1", 0), _FakeOllama)
    server.requests = []
    server.responder = lambda body: (200, ollama_chat_payload(scripted_reply(body["messages"])))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


# --------------------------------------------------------------------------- Hugging Face


@pytest.fixture(scope="session")
def tiny_hf_models(tmp_path_factory):
    """A tiny chat model and a tiny sentence encoder, built locally with random weights.

    Nothing is downloaded. The models are real ``transformers`` and
    ``sentence-transformers`` objects saved to disk, so loading, chat templating,
    tokenising, seeded generation and encoding all go through the libraries' own code.
    Their outputs are meaningless.
    """
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    pytest.importorskip("sentence_transformers")
    import warnings

    from sentence_transformers import SentenceTransformer
    from sentence_transformers import models as st_models
    from tokenizers import Tokenizer, models, pre_tokenizers, trainers
    from transformers import (
        BertConfig,
        BertModel,
        LlamaConfig,
        LlamaForCausalLM,
        PreTrainedTokenizerFast,
    )

    root = tmp_path_factory.mktemp("tiny-hf")
    corpus = [
        "the agent scans and charges the battery when it is low",
        "system user assistant you are a careful scientist measure the sample",
        "action think scan charge downlink desat status success failure",
    ]

    def tokenizer(specials):
        tok = Tokenizer(models.WordLevel(unk_token="[UNK]"))
        tok.pre_tokenizer = pre_tokenizers.Whitespace()
        tok.train_from_iterator(corpus, trainers.WordLevelTrainer(special_tokens=specials))
        return tok

    chat_tok = PreTrainedTokenizerFast(
        tokenizer_object=tokenizer(["[UNK]", "[PAD]", "<s>", "</s>"]),
        unk_token="[UNK]",
        pad_token="[PAD]",
        bos_token="<s>",
        eos_token="</s>",
    )
    chat_tok.chat_template = (
        "{% for m in messages %}<s> {{ m['role'] }} : {{ m['content'] }} </s> {% endfor %}"
        "{% if add_generation_prompt %}<s> assistant : {% endif %}"
    )
    torch.manual_seed(0)
    chat = LlamaForCausalLM(
        LlamaConfig(
            vocab_size=len(chat_tok),
            hidden_size=16,
            intermediate_size=32,
            num_hidden_layers=1,
            num_attention_heads=2,
            num_key_value_heads=2,
            max_position_embeddings=64,
            bos_token_id=chat_tok.bos_token_id,
            eos_token_id=chat_tok.eos_token_id,
            pad_token_id=chat_tok.pad_token_id,
        )
    )
    chat_dir = root / "tiny-chat"
    chat.save_pretrained(chat_dir)
    chat_tok.save_pretrained(chat_dir)

    enc_tok = PreTrainedTokenizerFast(
        tokenizer_object=tokenizer(["[UNK]", "[PAD]", "[CLS]", "[SEP]", "[MASK]"]),
        unk_token="[UNK]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        sep_token="[SEP]",
        mask_token="[MASK]",
    )
    bert = BertModel(
        BertConfig(
            vocab_size=len(enc_tok),
            hidden_size=16,
            num_hidden_layers=1,
            num_attention_heads=2,
            intermediate_size=32,
            max_position_embeddings=64,
            pad_token_id=enc_tok.pad_token_id,
        )
    )
    bert_dir = root / "tiny-bert"
    bert.save_pretrained(bert_dir)
    enc_tok.save_pretrained(bert_dir)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        word = st_models.Transformer(str(bert_dir), max_seq_length=64)
        pool = st_models.Pooling(word.get_word_embedding_dimension(), pooling_mode="mean")
        encoder = SentenceTransformer(modules=[word, pool], device="cpu")
    encoder_dir = root / "tiny-encoder"
    encoder.save(str(encoder_dir))
    return {"chat": chat_dir, "encoder": encoder_dir}
