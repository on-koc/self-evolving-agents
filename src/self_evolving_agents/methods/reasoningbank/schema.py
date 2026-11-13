"""Memory records of ReasoningBank.

The memory item is the paper's (section 3.2): a title, a one-sentence description
and the content. An experience is one entry of the bank as the paper stores it
(Appendix A.2): the task query, the trajectory it produced and the items distilled
from it. Trajectories live in the provenance store and are referenced by id.
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


@dataclass
class MemoryItem:
    """A distilled, reusable piece of strategy.

    * ``title`` – concise identifier of the strategy or reasoning pattern.
    * ``description`` – one-sentence summary of the item.
    * ``content`` – the distilled reasoning steps, rationale or operational insight.

    ``meta`` is free for methods built on top to attach their own bookkeeping; the
    baseline never reads it.
    """

    title: str
    description: str
    content: str
    id: str = field(default_factory=lambda: new_id("mem"))
    source: str = SOURCE_SUCCESS
    experience_id: str = ""
    created_at: float = field(default_factory=time.time)
    meta: dict[str, Any] = field(default_factory=dict)

    def render(self, index: int | None = None, with_description: bool = False) -> str:
        """The item as it is shown to the agent.

        The paper represents each item "by its title and content" (Appendix A.2).
        ``with_description=True`` gives the form the reference code injects: the
        extractor's Markdown with all three fields.
        """
        head = f"# Memory Item {index}" if index is not None else "# Memory Item"
        lines = [head, f"## Title {self.title}"]
        if with_description:
            lines.append(f"## Description {self.description}")
        lines.append(f"## Content {self.content}")
        return "\n".join(lines)

    @property
    def text(self) -> str:
        """All three fields as one string (for methods that embed items)."""
        return f"{self.title}. {self.description} {self.content}"

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
            meta=dict(d.get("meta") or {}),
        )


@dataclass
class Experience:
    """One entry of the bank: a task query, the trajectories it produced, the items distilled.

    ``task`` is the task record the entry came from, kept for provenance and for
    methods built on top. The baseline retrieves by ``query`` alone.
    """

    query: str
    items: list[MemoryItem]
    id: str = field(default_factory=lambda: new_id("exp"))
    task_key: str = ""
    task: dict[str, Any] = field(default_factory=dict)
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
                "task": self.task,
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
            task=dict(d.get("task") or {}),
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
    are dropped rather than guessed at. ``limit`` enforces the prompt's "at most N
    items" on the model's reply.
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
