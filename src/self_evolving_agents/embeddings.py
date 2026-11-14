"""Text embeddings for memory retrieval.

The paper embeds task queries with ``gemini-embedding-001``; :class:`GeminiEmbedder`
is that model. The default is a dependency-free hashing embedder so that retrieval
works offline; it captures lexical overlap (shared words and character n-grams), not
meaning, and a run that uses it is not using the paper's retrieval.

Three more embedders cover the usual ways of running an embedding model:
:class:`OpenAIEmbedder` (any server with an OpenAI-style ``/v1/embeddings``),
:class:`OllamaEmbedder` (an Ollama server) and :class:`HuggingFaceEmbedder` (a model
run on this machine with ``sentence-transformers``). Any object with a ``name`` and an
``embed`` method can be passed instead.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an ``(n, d)`` array of L2-normalised row vectors."""
        ...


_WORD = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def _bucket(token: str, dim: int) -> tuple[int, float]:
    digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
    value = int.from_bytes(digest, "little")
    return value % dim, 1.0 if (value >> 63) & 1 else -1.0


class HashingEmbedder:
    """Feature hashing over words, word bigrams and character trigrams.

    Signed hashing keeps collisions unbiased, and sub-linear term weighting stops a
    frequently repeated token from dominating. Deterministic across processes and
    machines (it does not rely on Python's salted ``hash``).
    """

    def __init__(self, dim: int = 1024, char_ngrams: bool = True):
        self.dim = dim
        self.char_ngrams = char_ngrams
        self.name = f"hashing-{dim}{'-c3' if char_ngrams else ''}"

    def _tokens(self, text: str) -> list[str]:
        words = _WORD.findall(text.lower())
        tokens = [f"w:{w}" for w in words]
        tokens += [f"b:{a}_{b}" for a, b in zip(words, words[1:], strict=False)]
        if self.char_ngrams:
            for w in words:
                padded = f"^{w}$"
                tokens += [f"c:{padded[i : i + 3]}" for i in range(len(padded) - 2)]
        return tokens

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            counts: dict[str, int] = {}
            for token in self._tokens(text):
                counts[token] = counts.get(token, 0) + 1
            for token, count in counts.items():
                index, sign = _bucket(token, self.dim)
                out[row, index] += sign * (1.0 + math.log(count))
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


def cosine_matrix(queries: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """Cosine similarity between every query row and every corpus row."""
    if corpus.size == 0:
        return np.zeros((queries.shape[0], 0), dtype=np.float32)
    return queries @ corpus.T


def condition_similarity(a: dict[str, Any], b: dict[str, Any]) -> float | None:
    """Similarity in ``[0, 1]`` between two operating-condition dictionaries.

    Numeric values that are both positive are compared on a log scale (a battery
    twice as large is as far away as one half as large); other numbers are compared
    relative to their magnitude; everything else must match exactly. Only keys
    present in both dictionaries are compared. Returns ``None`` when there is
    nothing to compare, so that callers can fall back to text similarity alone.
    """
    shared = [k for k in a if k in b]
    if not shared:
        return None
    total = 0.0
    for key in shared:
        x, y = a[key], b[key]
        numeric = (
            isinstance(x, (int, float))
            and isinstance(y, (int, float))
            and not isinstance(x, bool)
            and not isinstance(y, bool)
        )
        if numeric:
            if x > 0 and y > 0:
                distance = abs(math.log(x / y))
            else:
                scale = max(abs(x), abs(y), 1e-12)
                distance = abs(x - y) / scale
            total += math.exp(-distance)
        else:
            total += 1.0 if x == y else 0.0
    return total / len(shared)


class GeminiEmbedder:
    """``gemini-embedding-001`` through the official Google GenAI SDK.

    This is the embedding model the ReasoningBank paper uses (Appendix A.2), called
    the way the reference code calls it: task type ``RETRIEVAL_DOCUMENT`` and 3072
    output dimensions. It needs the ``gemini`` extra and Google credentials
    (``GOOGLE_API_KEY``, or a Vertex AI project).

    It has been exercised against a local stand-in for the service only, never
    against the service itself.
    """

    def __init__(
        self,
        model: str = "gemini-embedding-001",
        *,
        dimensions: int = 3072,
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: int = 64,
        client: Any = None,
    ):
        if client is None:
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover - depends on the optional extra
                raise ImportError(
                    "GeminiEmbedder needs the Google GenAI SDK: "
                    "pip install 'self-evolving-agents[gemini]'"
                ) from exc
            client = genai.Client()
        self.client = client
        self.model = model
        self.dimensions = dimensions
        self.task_type = task_type
        self.batch_size = batch_size
        self.name = f"{model}-{dimensions}"

    def embed(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            response = self.client.models.embed_content(
                model=self.model,
                contents=list(texts[start : start + self.batch_size]),
                config={
                    "task_type": self.task_type,
                    "output_dimensionality": self.dimensions,
                },
            )
            rows.extend(list(e.values) for e in response.embeddings)
        if len(rows) != len(texts):
            raise RuntimeError(f"asked for {len(texts)} embeddings, received {len(rows)}")
        out = np.asarray(rows, dtype=np.float32).reshape(len(texts), -1)
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


def _unit_rows(rows: Any, expected: int) -> np.ndarray:
    """Vectors as float32 rows of length one, after checking that none is missing."""
    out = np.asarray(rows, dtype=np.float32)
    if out.ndim != 2 or out.shape[0] != expected:
        raise RuntimeError(f"asked for {expected} embeddings, received shape {out.shape}")
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return out / norms


class OpenAIEmbedder:
    """An embedding model behind an OpenAI-style ``/v1/embeddings`` endpoint.

    Works with OpenAI and with the servers that imitate it (vLLM, llama.cpp,
    text-embeddings-inference, LM Studio, Ollama's ``/v1``). ``base_url`` is the
    server's address; the key is read from the environment variable ``api_key_env``.
    """

    def __init__(
        self,
        model: str,
        *,
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        dimensions: int | None = None,
        batch_size: int = 64,
        timeout: float = 120.0,
        client: Any = None,
    ):
        if not model:
            raise ValueError("an OpenAI-compatible embedder needs a model name: openai:<model>")
        if client is None:
            try:
                import openai
            except ImportError as exc:  # pragma: no cover - depends on the optional extra
                raise ImportError(
                    "OpenAIEmbedder needs the openai SDK: pip install 'self-evolving-agents[openai]'"
                ) from exc
            import os

            key = os.environ.get(api_key_env) or ("not-needed" if base_url else None)
            client = openai.OpenAI(api_key=key, base_url=base_url, timeout=timeout)
        self.client = client
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.name = f"openai-{model}" + (f"-{dimensions}" if dimensions else "")

    def embed(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            kwargs: dict[str, Any] = {
                "model": self.model,
                "input": list(texts[start : start + self.batch_size]),
                "encoding_format": "float",
            }
            if self.dimensions:
                kwargs["dimensions"] = int(self.dimensions)
            response = self.client.embeddings.create(**kwargs)
            # The protocol returns an index with each vector; do not rely on the order.
            for item in sorted(response.data, key=lambda d: d.index):
                rows.append(list(item.embedding))
        return _unit_rows(rows, len(texts)) if texts else np.zeros((0, 0), dtype=np.float32)


class OllamaEmbedder:
    """An embedding model served by Ollama (``/api/embed``), through the official client."""

    def __init__(
        self,
        model: str,
        *,
        host: str | None = None,
        batch_size: int = 32,
        options: dict[str, Any] | None = None,
        keep_alive: float | str | None = None,
        timeout: float = 120.0,
        client: Any = None,
    ):
        if not model:
            raise ValueError("an Ollama embedder needs a model name: ollama:<model>")
        if client is None:
            try:
                import ollama
            except ImportError as exc:  # pragma: no cover - depends on the optional extra
                raise ImportError(
                    "OllamaEmbedder needs the ollama client: "
                    "pip install 'self-evolving-agents[ollama]'"
                ) from exc
            client = ollama.Client(host=host, timeout=timeout)
        self.client = client
        self.model = model
        self.batch_size = batch_size
        self.options = dict(options or {})
        self.keep_alive = keep_alive
        self.name = f"ollama-{model}"

    def embed(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            response = self.client.embed(
                model=self.model,
                input=list(texts[start : start + self.batch_size]),
                # A text longer than the model's window must be an error, not a silent cut.
                truncate=False,
                options=self.options or None,
                keep_alive=self.keep_alive,
            )
            rows.extend(list(vector) for vector in response.embeddings)
        return _unit_rows(rows, len(texts)) if texts else np.zeros((0, 0), dtype=np.float32)


class HuggingFaceEmbedder:
    """An embedding model run on this machine with ``sentence-transformers``.

    ``prefix`` is put before every text, for models trained with one (``"query: "``
    for the E5 family). Retrieval here compares task descriptions with task
    descriptions, so one prefix serves both sides. Pin ``revision`` for a run that
    has to be repeatable.
    """

    def __init__(
        self,
        model: str,
        *,
        device: str | None = None,
        batch_size: int = 32,
        prefix: str = "",
        revision: str | None = None,
        trust_remote_code: bool = False,
        encoder: Any = None,
    ):
        if not model:
            raise ValueError("a Hugging Face embedder needs a model name: hf:<model>")
        if encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - depends on the optional extra
                raise ImportError(
                    "HuggingFaceEmbedder needs sentence-transformers: "
                    "pip install 'self-evolving-agents[huggingface]'"
                ) from exc
            encoder = SentenceTransformer(
                model, device=device, revision=revision, trust_remote_code=trust_remote_code
            )
        self.encoder = encoder
        self.model = model
        self.batch_size = batch_size
        self.prefix = prefix
        self.name = f"hf-{model}" + (f"@{revision}" if revision else "")

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        vectors = self.encoder.encode(
            [self.prefix + text for text in texts],
            batch_size=self.batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return _unit_rows(vectors, len(texts))


class CachedEmbedder:
    """Remembers vectors on disk, so a text is sent to the embedding service once.

    The paper stores the embedding of every query next to the memory for the same
    reason. Reloading a bank then costs nothing and returns the same vectors.
    """

    def __init__(self, embedder: Embedder, path: str | Path):
        self.embedder = embedder
        self.path = Path(path)
        self.name = embedder.name
        self._vectors: dict[str, np.ndarray] = {}
        if self.path.exists():
            with self.path.open() as fh:
                for line in fh:
                    if line.strip():
                        record = json.loads(line)
                        if record.get("embedder") == self.name:
                            self._vectors[record["key"]] = np.asarray(
                                record["vector"], dtype=np.float32
                            )

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.blake2b(text.encode(), digest_size=16).hexdigest()

    def embed(self, texts: list[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if self._key(t) not in self._vectors]
        if missing:
            vectors = self.embedder.embed(missing)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as fh:
                for text, vector in zip(missing, vectors, strict=True):
                    self._vectors[self._key(text)] = vector
                    record = {
                        "embedder": self.name,
                        "key": self._key(text),
                        "vector": vector.tolist(),
                    }
                    fh.write(json.dumps(record) + "\n")
        return np.stack([self._vectors[self._key(t)] for t in texts]) if texts else np.zeros((0, 0))


def make_embedder(
    spec: str = "hashing", cache_dir: str | Path | None = None, **options: Any
) -> Embedder:
    """An embedder from a short description.

    * ``hashing`` or ``hashing:<dim>``: the offline word-overlap embedder.
    * ``gemini`` or ``gemini:<model>``: the paper's embedding model.
    * ``openai:<model>`` or ``openai:<model>@<address>``: an OpenAI-style embeddings
      endpoint.
    * ``ollama:<model>`` or ``ollama:<model>@<address>``: an Ollama server.
    * ``hf:<model>``: a ``sentence-transformers`` model on this machine.

    Every embedder but the hashing one is cached on disk when ``cache_dir`` is given,
    so that a text is embedded once and a reloaded memory gets identical vectors.
    ``options`` are passed to the embedder's constructor.
    """
    from .llm.specs import split_spec

    kind, detail, address = split_spec(spec)
    embedder: Embedder
    if kind == "hashing":
        return HashingEmbedder(int(detail), **options) if detail else HashingEmbedder(**options)
    if kind == "gemini":
        embedder = GeminiEmbedder(detail, **options) if detail else GeminiEmbedder(**options)
    elif kind == "openai":
        if address:
            options = {"base_url": address, **options}
        embedder = OpenAIEmbedder(detail, **options)
    elif kind == "ollama":
        if address:
            options = {"host": address, **options}
        embedder = OllamaEmbedder(detail, **options)
    elif kind == "hf":
        embedder = HuggingFaceEmbedder(detail, **options)
    else:
        raise ValueError(
            f"unknown embedder {spec!r}; use 'hashing', 'gemini', 'openai:<model>', "
            "'ollama:<model>' or 'hf:<model>'"
        )
    if cache_dir is not None:
        embedder = CachedEmbedder(embedder, Path(cache_dir) / "embeddings.jsonl")
    return embedder
