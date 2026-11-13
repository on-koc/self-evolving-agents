"""The memory bank of ReasoningBank: storage, retrieval and consolidation, as published.

* **Retrieval** (Appendix A.2): the task query is embedded, past experiences are
  ranked by cosine similarity of their queries, and all memory items of the top-k
  experiences are returned. k = 1 by default.
* **Consolidation**: new experiences are appended. Nothing is pruned, merged or
  de-duplicated.

Nothing else lives here. Retrieval that looks at anything other than the query, and
any consolidation beyond appending, belong to the methods built on top.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ...embeddings import Embedder, HashingEmbedder
from .schema import Experience, MemoryItem

TIE_BREAKS = ("oldest", "newest")


@dataclass
class Retrieved:
    item: MemoryItem
    experience_id: str
    score: float


class ReasoningBank:
    """An append-only store of experiences and the memory items distilled from them.

    Args:
        path: JSON Lines file, one experience per line (``None`` keeps it in memory).
        embedder: embeds task queries. The paper uses ``gemini-embedding-001``
            (``embeddings.GeminiEmbedder``); the default is an offline hashing
            embedder that measures word overlap.
        query_instruction: if given, the lookup vector is the embedding of
            ``"Instruct: <instruction>\\nQuery: <query>"`` while stored vectors stay
            embeddings of the plain query. The reference code does this; the paper
            does not mention it. Off by default.
        tie_break: which experience wins when several are equally similar.
            ``"oldest"`` is what the reference code's stable sort does. Exact ties are
            rare on the paper's benchmarks; they are the normal case in a stream that
            repeats one task statement, where ``"oldest"`` keeps returning the first
            experience ever stored. See ``docs/methods/reasoningbank.md``.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        embedder: Embedder | None = None,
        *,
        query_instruction: str | None = None,
        tie_break: str = "oldest",
    ):
        if tie_break not in TIE_BREAKS:
            raise ValueError(f"tie_break must be one of {TIE_BREAKS}")
        self.path = Path(path) if path else None
        self.embedder: Embedder = embedder or HashingEmbedder()
        self.query_instruction = query_instruction
        self.tie_break = tie_break
        self.experiences: list[Experience] = []
        self._query_vecs: list[np.ndarray] = []
        if self.path and self.path.exists():
            self._load()

    # ------------------------------------------------------------------ storage

    def _load(self) -> None:
        assert self.path is not None
        with self.path.open() as fh:
            loaded = [Experience.from_dict(json.loads(line)) for line in fh if line.strip()]
        if loaded:
            vectors = self.embedder.embed([e.query for e in loaded])
            self._query_vecs = list(vectors)
            self.experiences = loaded

    def save(self) -> None:
        """Write the bank as JSON Lines, one experience per line."""
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w") as fh:
            for experience in self.experiences:
                fh.write(json.dumps(experience.to_dict()) + "\n")
        tmp.replace(self.path)

    def __len__(self) -> int:
        return len(self.experiences)

    @property
    def items(self) -> list[MemoryItem]:
        return [item for experience in self.experiences for item in experience.items]

    def get_item(self, item_id: str) -> MemoryItem | None:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    # ------------------------------------------------------------------ consolidation

    def add(self, experience: Experience) -> Experience:
        """Consolidate a new experience: append it (Appendix A.2, "Memory Consolidation")."""
        self._query_vecs.append(self.embedder.embed([experience.query])[0])
        self.experiences.append(experience)
        self.save()
        return experience

    # ------------------------------------------------------------------ retrieval

    def _lookup_vector(self, query: str) -> np.ndarray:
        text = query
        if self.query_instruction:
            text = f"Instruct: {self.query_instruction}\nQuery: {query}"
        return self.embedder.embed([text])[0]

    def similarities(self, query: str) -> np.ndarray:
        """Cosine similarity of ``query`` to the query of every stored experience."""
        if not self.experiences:
            return np.zeros(0, dtype=np.float32)
        return np.stack(self._query_vecs) @ self._lookup_vector(query)

    def rank(self, query: str) -> list[tuple[int, float]]:
        """Indices of the stored experiences, most similar first, with their scores."""
        scores = self.similarities(query)
        newest_first = self.tie_break == "newest"
        order = sorted(
            range(len(scores)),
            key=lambda i: (-round(float(scores[i]), 9), -i if newest_first else i),
        )
        return [(i, float(scores[i])) for i in order]

    def retrieve(self, query: str, *, k: int = 1) -> list[Retrieved]:
        """All memory items of the ``k`` experiences whose queries are most similar.

        An experience from which nothing could be extracted has no items; if it is
        the best match, nothing is returned for it, as in the reference code.
        """
        out: list[Retrieved] = []
        for index, score in self.rank(query)[: max(k, 0)]:
            experience = self.experiences[index]
            out.extend(Retrieved(item, experience.id, score) for item in experience.items)
        return out

    # ------------------------------------------------------------------ reporting

    def stats(self) -> dict[str, Any]:
        items = self.items
        by_source: dict[str, int] = {}
        for item in items:
            by_source[item.source] = by_source.get(item.source, 0) + 1
        return {
            "experiences": len(self.experiences),
            "items": len(items),
            "items_by_source": by_source,
            "embedder": self.embedder.name,
        }
