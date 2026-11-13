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
