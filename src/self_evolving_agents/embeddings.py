"""Text embeddings for memory retrieval.

The paper embeds task queries with ``gemini-embedding-001``. The default here is a
dependency-free hashing embedder so that retrieval works offline; it captures
lexical overlap (shared words and character n-grams), not meaning. Any object with
the same two methods can be passed instead, e.g. a wrapper around a sentence
embedding model or an embeddings API.
"""

from __future__ import annotations

import hashlib
import math
import re
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
