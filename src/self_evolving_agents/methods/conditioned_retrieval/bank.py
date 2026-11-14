"""A memory bank whose retrieval looks at more than the task query. Not from the paper.

In the paper every task has its own query, and the most similar past query is a
sensible thing to retrieve. A simulation task family is different: every episode can
share one task statement and differ only in the operating conditions, so all past
queries look alike and "the most similar experience" is an arbitrary one.

:class:`ConditionedBank` adds four things to the published bank, each switched
separately:

* **item-level retrieval** – score individual items instead of whole experiences;
* **condition similarity** – weigh in how close the stored operating conditions are
  to the current ones;
* **usage statistics** – prefer items whose past uses went well;
* **diversity** – do not return several near-identical items;

and one thing to consolidation:

* **duplicate filter** – drop a new item that nearly repeats an existing one.

None of these has been evaluated with a language model. They are hypotheses about
what the simulation setting needs.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from ...embeddings import Embedder, condition_similarity
from ..reasoningbank.bank import ReasoningBank, Retrieved
from ..reasoningbank.schema import Experience, MemoryItem

MODES = ("experience", "item")


class ConditionedBank(ReasoningBank):
    """The published bank plus condition-aware, item-level retrieval and a duplicate filter."""

    def __init__(
        self,
        path: str | Path | None = None,
        embedder: Embedder | None = None,
        *,
        dedup_threshold: float | None = None,
        tie_break: str = "newest",
    ):
        self.dedup_threshold = dedup_threshold
        self._item_vecs: dict[str, np.ndarray] = {}
        super().__init__(path, embedder, tie_break=tie_break)
        for experience in self.experiences:
            self._index_items(experience)

    def _index_items(self, experience: Experience) -> None:
        if not experience.items:
            return
        vectors = self.embedder.embed([item.text for item in experience.items])
        for item, vector in zip(experience.items, vectors, strict=True):
            self._item_vecs[item.id] = vector

    # ------------------------------------------------------------------ consolidation

    def add(self, experience: Experience) -> Experience:
        """Append, after dropping new items that nearly repeat an existing one (if enabled)."""
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
        self._index_items(experience)
        return super().add(experience)

    def record_outcome(self, item_ids: Iterable[str], score: float, success: bool | None) -> None:
        """Update the usage statistics of the items an episode was given."""
        wanted = set(item_ids)
        if not wanted:
            return
        for item in self.items:
            if item.id in wanted:
                usage = item.meta.setdefault("usage", {"uses": 0, "score_sum": 0.0, "successes": 0})
                usage["uses"] += 1
                usage["score_sum"] += float(score)
                usage["successes"] += int(bool(success))
        self.save()

    @staticmethod
    def mean_score(item: MemoryItem) -> float | None:
        usage = item.meta.get("usage") or {}
        return usage["score_sum"] / usage["uses"] if usage.get("uses") else None

    # ------------------------------------------------------------------ retrieval

    def retrieve_conditioned(
        self,
        query: str,
        *,
        k: int = 1,
        mode: str = "item",
        max_items: int = 6,
        conditions: dict[str, Any] | None = None,
        condition_weight: float = 0.5,
        utility_weight: float = 0.0,
        diversity: float = 0.3,
    ) -> list[Retrieved]:
        """Memory items relevant to ``query`` under ``conditions``.

        Args:
            k: ``experience`` mode: number of experiences to take items from.
            mode: ``"experience"`` ranks experiences (as the paper does, but with the
                blended relevance below); ``"item"`` ranks individual items.
            max_items: cap on the number of items returned.
            conditions: operating conditions of the current task.
            condition_weight: 0..1, share of the relevance given to condition
                similarity instead of query similarity. 0 ignores conditions.
            utility_weight: ``item`` mode. Bonus for items whose past uses scored above
                the bank's average, penalty for those below.
            diversity: ``item`` mode. 0 ranks purely by relevance; larger values
                penalise items similar to ones already selected.
        """
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if not self.experiences:
            return []
        query_vec = self._lookup_vector(query)
        relevance = np.stack(self._query_vecs) @ query_vec
        if condition_weight and conditions:
            for i, experience in enumerate(self.experiences):
                stored = (experience.task or {}).get("conditions") or {}
                similarity = condition_similarity(conditions, stored)
                if similarity is not None:
                    relevance[i] = (1.0 - condition_weight) * relevance[
                        i
                    ] + condition_weight * similarity

        if mode == "experience":
            newest_first = self.tie_break == "newest"
            order = sorted(
                range(len(relevance)),
                key=lambda i: (-round(float(relevance[i]), 9), -i if newest_first else i),
            )
            out: list[Retrieved] = []
            for i in order[: max(k, 0)]:
                experience = self.experiences[i]
                out.extend(
                    Retrieved(item, experience.id, float(relevance[i])) for item in experience.items
                )
            return out[:max_items]

        pool: list[tuple[MemoryItem, str, float, np.ndarray]] = []
        for i, experience in enumerate(self.experiences):
            for item in experience.items:
                vector = self._item_vecs[item.id]
                # An item is relevant if it reads like the query or comes from a similar task.
                score = 0.5 * float(vector @ query_vec) + 0.5 * float(relevance[i])
                pool.append((item, experience.id, score, vector))
        if not pool:
            return []
        if utility_weight:
            used = [m for m in (self.mean_score(p[0]) for p in pool) if m is not None]
            if len(used) >= 2 and float(np.std(used)) > 1e-9:
                mean, std = float(np.mean(used)), float(np.std(used))

                def bonus(item: MemoryItem) -> float:
                    value = self.mean_score(item)
                    if value is None:
                        return 0.0
                    return utility_weight * float(np.clip((value - mean) / std, -2, 2)) / 2

                pool = [(item, eid, score + bonus(item), vec) for item, eid, score, vec in pool]
        return self._select_diverse(pool, max_items, diversity)

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

    def stats(self) -> dict[str, Any]:
        out = super().stats()
        out["items_used"] = sum(1 for i in self.items if (i.meta.get("usage") or {}).get("uses"))
        return out
