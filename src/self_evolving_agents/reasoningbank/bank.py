"""The memory bank: storage, retrieval and consolidation.

Two retrieval modes are provided.

``experience`` is the paper's method: embed the current task query, find the top-k
most similar *past experiences* by cosine similarity of their queries, and return
all memory items of those experiences (k = 1 by default).

``item`` is an adaptation for simulation task families. When every episode shares
one task statement and differs only in operating conditions, all past queries look
alike and "the most similar experience" is an arbitrary one. Item mode scores
individual items instead, can weigh in how close the stored operating conditions
are to the current ones, can prefer items whose past uses went well, and
diversifies the selection so that five near-identical lessons do not crowd out a
sixth different one.

Consolidation is the paper's: new experiences are appended. An optional duplicate
filter is available and is off by default.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..embeddings import Embedder, HashingEmbedder, condition_similarity
from .schema import Experience, MemoryItem


@dataclass
class Retrieved:
    item: MemoryItem
    experience_id: str
    score: float


class ReasoningBank:
    """An append-only store of experiences and the memory items distilled from them."""

    def __init__(
        self,
        path: str | Path | None = None,
        embedder: Embedder | None = None,
        *,
        dedup_threshold: float | None = None,
    ):
        self.path = Path(path) if path else None
        self.embedder: Embedder = embedder or HashingEmbedder()
        self.dedup_threshold = dedup_threshold
        self.experiences: list[Experience] = []
        self._query_vecs: list[np.ndarray] = []
        self._item_vecs: dict[str, np.ndarray] = {}
        if self.path and self.path.exists():
            self._load()

    # ------------------------------------------------------------------ storage

    def _load(self) -> None:
        assert self.path is not None
        with self.path.open() as fh:
            loaded = [Experience.from_dict(json.loads(line)) for line in fh if line.strip()]
        for experience in loaded:
            self._index(experience)
            self.experiences.append(experience)

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

    def _index(self, experience: Experience) -> None:
        texts = [experience.query] + [item.text for item in experience.items]
        vectors = self.embedder.embed(texts)
        self._query_vecs.append(vectors[0])
        for item, vector in zip(experience.items, vectors[1:], strict=True):
            self._item_vecs[item.id] = vector

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
        """Consolidate a new experience into the bank (append, as in the paper).

        With ``dedup_threshold`` set, new items that are near-duplicates of an item
        already in the bank are dropped and listed in ``meta["dropped_duplicates"]``.
        """
        if self.dedup_threshold is not None and experience.items and self._item_vecs:
            existing_ids = list(self._item_vecs)
            existing = np.stack([self._item_vecs[i] for i in existing_ids])
            new_vecs = self.embedder.embed([item.text for item in experience.items])
            sims = new_vecs @ existing.T
            kept, dropped = [], []
            for row, item in enumerate(experience.items):
                best = int(np.argmax(sims[row]))
                if sims[row, best] >= self.dedup_threshold:
                    dropped.append({"title": item.title, "duplicate_of": existing_ids[best]})
                else:
                    kept.append(item)
            experience.items = kept
            if dropped:
                experience.meta["dropped_duplicates"] = dropped
        self._index(experience)
        self.experiences.append(experience)
        self.save()
        return experience

    def record_outcome(self, item_ids: Iterable[str], score: float, success: bool | None) -> None:
        """Update usage statistics of the items an episode was given."""
        wanted = set(item_ids)
        if not wanted:
            return
        for item in self.items:
            if item.id in wanted:
                item.record_use(score, success)
        self.save()

    # ------------------------------------------------------------------ retrieval

    def retrieve(
        self,
        query: str,
        *,
        k: int = 1,
        mode: str = "experience",
        max_items: int | None = None,
        conditions: dict[str, Any] | None = None,
        condition_weight: float = 0.0,
        utility_weight: float = 0.0,
        diversity: float = 0.3,
        exclude_task_keys: Sequence[str] = (),
    ) -> list[Retrieved]:
        """Return memory items relevant to ``query``.

        Args:
            k: number of experiences (``experience`` mode) to take items from.
            mode: ``"experience"`` (paper) or ``"item"`` (see module docstring).
            max_items: cap on returned items. Required for ``item`` mode; optional
                for ``experience`` mode.
            conditions: operating conditions of the current task, compared with those
                stored on each experience when ``condition_weight`` > 0.
            condition_weight: 0..1, share of the relevance score given to condition
                similarity instead of text similarity.
            utility_weight: ``item`` mode only. Adds a bonus for items whose past uses
                scored above the bank average, and a penalty for those below.
            diversity: ``item`` mode only. 0 ranks purely by relevance; larger values
                penalise items similar to ones already selected.
            exclude_task_keys: skip experiences that came from these exact tasks.
        """
        if mode not in ("experience", "item"):
            raise ValueError("mode must be 'experience' or 'item'")
        candidates = [
            i for i, e in enumerate(self.experiences) if e.task_key not in set(exclude_task_keys)
        ]
        if not candidates:
            return []
        query_vec = self.embedder.embed([query])[0]
        text_sim = np.array([float(self._query_vecs[i] @ query_vec) for i in candidates])
        relevance = self._blend(text_sim, candidates, conditions, condition_weight)

        if mode == "experience":
            # Ties (identical queries are common in simulation families) go to the newest.
            order = sorted(
                range(len(candidates)),
                key=lambda j: (
                    -round(float(relevance[j]), 9),
                    -self.experiences[candidates[j]].created_at,
                ),
            )
            out: list[Retrieved] = []
            for j in order[: max(k, 0)]:
                experience = self.experiences[candidates[j]]
                out.extend(
                    Retrieved(item, experience.id, float(relevance[j])) for item in experience.items
                )
            return out[:max_items] if max_items is not None else out

        if max_items is None:
            raise ValueError("item mode needs max_items")
        pool: list[tuple[MemoryItem, str, float, np.ndarray]] = []
        for j, index in enumerate(candidates):
            experience = self.experiences[index]
            for item in experience.items:
                vector = self._item_vecs[item.id]
                # An item is relevant if it reads like the query or comes from a similar task.
                score = 0.5 * float(vector @ query_vec) + 0.5 * float(relevance[j])
                pool.append((item, experience.id, score, vector))
        if not pool:
            return []
        if utility_weight:
            used = [p[0].mean_score for p in pool if p[0].uses]
            if len(used) >= 2 and float(np.std(used)) > 1e-9:
                mean, std = float(np.mean(used)), float(np.std(used))
                pool = [
                    (
                        item,
                        eid,
                        score
                        + (
                            utility_weight
                            * float(np.clip((item.mean_score - mean) / std, -2, 2))
                            / 2
                            if item.uses
                            else 0.0
                        ),
                        vec,
                    )
                    for item, eid, score, vec in pool
                ]
        return self._select_diverse(pool, max_items, diversity)

    def _blend(
        self,
        text_sim: np.ndarray,
        candidates: list[int],
        conditions: dict[str, Any] | None,
        weight: float,
    ) -> np.ndarray:
        if not weight or not conditions:
            return text_sim
        blended = text_sim.copy()
        for j, index in enumerate(candidates):
            similarity = condition_similarity(conditions, self.experiences[index].conditions)
            if similarity is not None:
                blended[j] = (1.0 - weight) * text_sim[j] + weight * similarity
        return blended

    @staticmethod
    def _select_diverse(
        pool: list[tuple[MemoryItem, str, float, np.ndarray]], n: int, diversity: float
    ) -> list[Retrieved]:
        """Greedy maximal-marginal-relevance selection; newer items win ties."""
        remaining = sorted(pool, key=lambda p: (-p[2], -p[0].created_at))
        chosen: list[tuple[MemoryItem, str, float, np.ndarray]] = []
        while remaining and len(chosen) < n:
            if not chosen or diversity <= 0:
                pick = 0
            else:
                picked = np.stack([c[3] for c in chosen])
                best_value, pick = -np.inf, 0
                for idx, (_item, _eid, score, vec) in enumerate(remaining):
                    redundancy = float(np.max(picked @ vec))
                    value = (1.0 - diversity) * score - diversity * redundancy
                    if value > best_value + 1e-12:
                        best_value, pick = value, idx
            chosen.append(remaining.pop(pick))
        return [Retrieved(item, eid, float(score)) for item, eid, score, _ in chosen]

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
            "items_used": sum(1 for i in items if i.uses),
        }
