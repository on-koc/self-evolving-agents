"""Text embeddings for memory retrieval.

The paper embeds task queries with ``gemini-embedding-001``; :class:`GeminiEmbedder`
is that model. The default is a dependency-free hashing embedder so that retrieval
works offline; it captures lexical overlap (shared words and character n-grams), not
meaning, and a run that uses it is not using the paper's retrieval. Any object with
a ``name`` and an ``embed`` method can be passed instead.
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


def make_embedder(spec: str = "hashing", cache_dir: str | Path | None = None) -> Embedder:
    """An embedder from a short description.

    ``"hashing"`` or ``"hashing:<dim>"``: the offline word-overlap embedder.
    ``"gemini"`` or ``"gemini:<model>"``: the paper's embedding model, cached on disk
    when ``cache_dir`` is given.
    """
    kind, _, detail = spec.partition(":")
    if kind == "hashing":
        return HashingEmbedder(int(detail)) if detail else HashingEmbedder()
    if kind == "gemini":
        embedder: Embedder = GeminiEmbedder(detail) if detail else GeminiEmbedder()
        if cache_dir is not None:
            embedder = CachedEmbedder(embedder, Path(cache_dir) / "embeddings.jsonl")
        return embedder
    raise ValueError(f"unknown embedder {spec!r}; use 'hashing' or 'gemini'")
