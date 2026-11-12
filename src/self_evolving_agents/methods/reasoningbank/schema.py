"""Memory records.

The memory item follows the ReasoningBank schema exactly (title, description,
content). Everything else here is bookkeeping around it: which experience an item
came from, how it was produced, and how episodes that used it turned out.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from ...types import jsonable, new_id

#: How an item was produced.
SOURCE_SUCCESS = "success"  # distilled from a trajectory judged successful
SOURCE_FAILURE = "failure"  # distilled from a trajectory judged failed
SOURCE_CONTRAST = "contrast"  # self-contrast across several trajectories (MaTTS parallel)
SOURCE_REFINE = "refine"  # from attempts and refinement notes (MaTTS sequential)
SOURCE_CLAIM = "claim"  # rendered from an evidence-backed claim (phase 2)


@dataclass
class MemoryItem:
    """A distilled, reusable piece of strategy.

    * ``title`` – concise identifier of the strategy or reasoning pattern.
    * ``description`` – one sentence on when (and when not) to use it.
    * ``content`` – the distilled reasoning steps, rationale or operational insight.
    """

    title: str
    description: str
    content: str
    id: str = field(default_factory=lambda: new_id("mem"))
    source: str = SOURCE_SUCCESS
    experience_id: str = ""
    created_at: float = field(default_factory=time.time)
    # Usage statistics, updated as episodes that retrieved this item finish.
    uses: int = 0
    score_sum: float = 0.0
    successes: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def render(self, index: int | None = None) -> str:
        head = f"# Memory Item {index}" if index is not None else "# Memory Item"
        return (
            f"{head}\n## Title {self.title}\n## Description {self.description}\n"
            f"## Content {self.content}"
        )

    @property
    def text(self) -> str:
        """Text used to embed the item for item-level retrieval."""
        return f"{self.title}. {self.description} {self.content}"

    @property
    def mean_score(self) -> float | None:
        return self.score_sum / self.uses if self.uses else None

    def record_use(self, score: float, success: bool | None) -> None:
        self.uses += 1
        self.score_sum += float(score)
        self.successes += int(bool(success))

    def to_dict(self) -> dict[str, Any]:
        return jsonable(
            {
                "id": self.id,
                "title": self.title,
                "description": self.description,
                "content": self.content,
                "source": self.source,
                "experience_id": self.experience_id,
                "created_at": self.created_at,
                "uses": self.uses,
                "score_sum": self.score_sum,
                "successes": self.successes,
                "meta": self.meta,
            }
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MemoryItem:
        return cls(
            title=d["title"],
            description=d.get("description", ""),
            content=d.get("content", ""),
            id=d.get("id") or new_id("mem"),
            source=d.get("source", SOURCE_SUCCESS),
            experience_id=d.get("experience_id", ""),
            created_at=float(d.get("created_at", 0.0)),
            uses=int(d.get("uses", 0)),
            score_sum=float(d.get("score_sum", 0.0)),
            successes=int(d.get("successes", 0)),
            meta=dict(d.get("meta") or {}),
        )


@dataclass
class Verdict:
    """A judgement of whether an episode succeeded, and who made it.

    ``source`` is ``"llm"`` for the LLM-as-a-judge used at test time (no ground
    truth), or ``"env"`` when the simulator's own success criterion was used.
    """

    success: bool
    thoughts: str = ""
    source: str = "llm"
    llm_call_id: str | None = None

    @property
    def label(self) -> str:
        return "success" if self.success else "failure"

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "thoughts": self.thoughts,
            "source": self.source,
            "llm_call_id": self.llm_call_id,
        }


@dataclass
class Experience:
    """One entry of the bank: a task query, the trajectories it produced, and the items distilled.

    This mirrors the paper's storage layout ("each entry consists of a task query, the
    original trajectory, and the corresponding memory items"); trajectories are kept
    in the provenance store and referenced here by id.
    """

    query: str
    items: list[MemoryItem]
    id: str = field(default_factory=lambda: new_id("exp"))
    task_key: str = ""
    task_family: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)
    trajectory_ids: list[str] = field(default_factory=list)
    verdict: str = ""
    created_at: float = field(default_factory=time.time)
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for item in self.items:
            item.experience_id = self.id

    def to_dict(self) -> dict[str, Any]:
        return jsonable(
            {
                "id": self.id,
                "query": self.query,
                "task_key": self.task_key,
                "task_family": self.task_family,
                "conditions": self.conditions,
                "trajectory_ids": self.trajectory_ids,
                "verdict": self.verdict,
                "created_at": self.created_at,
                "meta": self.meta,
                "items": [i.to_dict() for i in self.items],
            }
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Experience:
        return cls(
            query=d["query"],
            items=[MemoryItem.from_dict(i) for i in d.get("items", [])],
            id=d.get("id") or new_id("exp"),
            task_key=d.get("task_key", ""),
            task_family=d.get("task_family", ""),
            conditions=dict(d.get("conditions") or {}),
            trajectory_ids=list(d.get("trajectory_ids") or []),
            verdict=d.get("verdict", ""),
            created_at=float(d.get("created_at", 0.0)),
            meta=dict(d.get("meta") or {}),
        )


_ITEM_SPLIT = re.compile(r"^\s*#\s*Memory Item\b[^\n]*$", re.MULTILINE | re.IGNORECASE)
_FIELD = re.compile(
    r"^\s*#{2,}\s*(Title|Description|Content)\b[ \t]*:?[ \t]*", re.MULTILINE | re.IGNORECASE
)


def parse_memory_items(text: str, source: str, limit: int | None = None) -> list[MemoryItem]:
    """Parse the extractor's Markdown output into items.

    Expected shape, per item::

        # Memory Item 1
        ## Title ...
        ## Description ...
        ## Content ...

    The parser tolerates code fences, a colon after the field name, values on the
    following line and multi-line content. Blocks without both a title and content
    are dropped rather than guessed at.
    """
    text = text.replace("```markdown", "").replace("```md", "").replace("```", "")
    blocks = _ITEM_SPLIT.split(text)[1:]
    items: list[MemoryItem] = []
    for block in blocks:
        fields: dict[str, str] = {}
        matches = list(_FIELD.finditer(block))
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(block)
            value = " ".join(block[match.end() : end].split())
            fields.setdefault(match.group(1).lower(), value.strip("*_ "))
        title, content = fields.get("title", ""), fields.get("content", "")
        if not title or not content:
            continue
        items.append(
            MemoryItem(
                title=title,
                description=fields.get("description", ""),
                content=content,
                source=source,
            )
        )
        if limit is not None and len(items) >= limit:
            break
    return items
