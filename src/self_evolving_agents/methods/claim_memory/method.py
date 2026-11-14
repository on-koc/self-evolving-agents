"""Claims as memory: an agent is shown the tested claims that apply to its task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...envs.base import TextEnv
from ...provenance import WAS_DERIVED_FROM, ProvenanceStore
from ...types import Task, Trajectory
from ..claim_graph.graph import ClaimGraph
from ..reasoningbank import prompts as published
from ..reasoningbank.method import ReasoningBankMemory
from ..reasoningbank.render import memory_block
from ..stream import Learned, Memory, Retrieval, Verdict
from .render import claims_as_memory


@dataclass
class ClaimMemoryConfig:
    #: Run directory of a finished claim study (it holds ``graph.json``).
    claims: str = ""
    #: Cap on the number of claims shown.
    max_claims: int = 8
    #: Also retrieve from, and learn into, a ReasoningBank (the "both" arm).
    with_reasoningbank: bool = False


class ClaimMemory(Memory):
    """Puts the claims that apply under the task's conditions in front of the agent.

    The claims come from a claim graph built beforehand by simulator experiments; the
    agent's own episodes add nothing to it. With ``base`` given, the items of a
    ReasoningBank are shown after the claims and that bank keeps learning as usual.

    Claims are rendered in the ReasoningBank item format, with their description,
    because the description is where a claim's scope is stated.
    """

    name = "claim_memory"

    def __init__(
        self,
        graph: ClaimGraph,
        *,
        base: ReasoningBankMemory | None = None,
        max_claims: int = 8,
        instruction: str = published.MEMORY_INSTRUCTION,
        store: ProvenanceStore | None = None,
    ):
        self.graph = graph
        self.base = base
        self.max_claims = max_claims
        self.instruction = instruction
        self.store = store
        self.learns = base is not None

    def retrieve(self, env: TextEnv, task: Task, query: str) -> Retrieval:
        claims = claims_as_memory(self.graph, task.conditions, max_items=self.max_claims)
        details: list[dict[str, Any]] = [
            {"item": c.id, "claim": c.meta["claim_id"], "distance": c.meta["distance"]}
            for c in claims
        ]
        items = list(claims)
        if self.base is not None:
            retrieved = self.base.retrieve_items(env, task, query)
            items += [r.item for r in retrieved]
            details += [
                {"item": r.item.id, "experience": r.experience_id, "score": round(r.score, 4)}
                for r in retrieved
            ]
        if self.store is not None:
            for item in claims:
                # Make the claim itself the thing that was used.
                self.store.add_node(item.id, "memory_item", label=item.title, data=item.to_dict())
                self.store.link(item.id, WAS_DERIVED_FROM, item.meta["claim_id"])
        block = memory_block(items, instruction=self.instruction, with_description=True)
        return Retrieval(block=block, details=details)

    def learn_single(
        self, env: TextEnv, task: Task, query: str, traj: Trajectory, verdict: Verdict
    ) -> Learned:
        if self.base is None:
            return Learned()
        return self.base.learn_single(env, task, query, traj, verdict)

    def stats(self) -> dict[str, Any]:
        out = {"claims": len(self.graph.claims)}
        if self.base is not None:
            out.update(self.base.stats())
        return out
