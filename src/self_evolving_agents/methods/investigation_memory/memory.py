"""The investigation memory as a memory method of the stream loop.

Before an episode it retrieves, by kind:

* **strategies**, from any task, ranked by how well their text matches the task and
  by their record of use;
* **hypotheses** from an earlier attempt in the same world, and, with their
  conditions, from other worlds of the same kind;
* **evidence** from an earlier attempt in the same world only.

After an episode it asks the model for evidence, hypotheses and strategies (one
call), and, in the same call, for an assessment of the strategies it had been shown.
The assessment updates their record, and a strategy that did not help can be
replaced by a narrower version. Nothing here sees the simulator's score; the episode
is labelled by the same judge ReasoningBank uses.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from ...embeddings import Embedder, HashingEmbedder
from ...envs.base import TextEnv
from ...llm import LLMRequest, extract_json_object, user
from ...provenance import WAS_DERIVED_FROM, WAS_GENERATED_BY, ProvenanceStore
from ...types import Task, Trajectory
from ..stream import Learned, Memory, Retrieval, Verdict
from . import prompts
from .config import InvestigationMemoryConfig
from .schema import (
    STATUSES,
    Evidence,
    Hypothesis,
    InvestigationGraph,
    Strategy,
    world_key,
    world_of,
)


def render_episode(traj: Trajectory, max_chars: int) -> str:
    """Each step's reasoning, action and result, as the agent saw them."""
    lines = []
    for step in traj.steps:
        thought = " ".join((step.thought or "").split())
        line = f"Step {step.index}: action {step.action}"
        if thought:
            line = f"Step {step.index}: reasoning: {thought[:600]} | action {step.action}"
        lines.append(f"{line} | result: {' '.join(step.result.split())[:500]}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        half = max_chars // 2
        text = text[:half] + "\n[... middle of the episode omitted ...]\n" + text[-half:]
    return text


def agent_notes(traj: Trajectory) -> str:
    """What the agent wrote down during the episode (the Hypothesizer's knowledge store)."""
    knowledge = traj.meta.get("scientific_knowledge")
    if knowledge:
        return prompts.render_json(knowledge)[:12000]
    return ""


class InvestigationMemory(Memory):
    name = "investigation_memory"

    def __init__(
        self,
        config: InvestigationMemoryConfig,
        llm: Any,
        *,
        path: Any = None,
        embedder: Embedder | None = None,
        store: ProvenanceStore | None = None,
    ):
        self.config = config
        self.llm = llm
        self.graph = InvestigationGraph(path)
        self.embedder = embedder or HashingEmbedder()
        self.store = store
        self.learns = config.mode in ("full", "answers", "placebo")

    # ------------------------------------------------------------------ retrieval

    def _rank_strategies(self, query: str) -> list[Strategy]:
        candidates = self.graph.active_strategies()
        if not candidates:
            return []
        texts = [f"{s.statement} Applies when: {s.applies_when}" for s in candidates]
        vectors = self.embedder.embed([query, *texts])
        similarity = vectors[1:] @ vectors[0]
        scores = [
            float(sim) * (0.5 + s.utility) for sim, s in zip(similarity, candidates, strict=True)
        ]
        order = np.argsort(-np.asarray(scores), kind="stable")
        return [candidates[i] for i in order[: self.config.max_strategies]]

    def retrieve(self, env: TextEnv, task: Task, query: str) -> Retrieval:
        mode = self.config.mode
        if mode == "instructed":
            return Retrieval(
                block=_block(prompts.INSTRUCTED, []), details=[{"kind": "instruction"}]
            )
        world = world_of(task)
        if mode == "answers":
            return self._answers(world)

        include = set(self.config.include)
        sections: list[str] = []
        ids: list[str] = []
        details: list[dict[str, Any]] = []
        if "strategies" in include:
            chosen = self._rank_strategies(query)
            if chosen:
                lines = []
                for n, s in enumerate(chosen, 1):
                    record = (
                        f" (used in {s.uses} earlier tasks: helped {s.helped}, did not help "
                        f"{s.did_not_help})"
                        if s.uses
                        else ""
                    )
                    lines.append(
                        f"S{n}. {s.statement}\n    When it applies: {s.applies_when}\n"
                        f"    How it was put into practice: {s.test}{record}"
                    )
                    ids.append(s.id)
                    details.append({"kind": "strategy", "id": s.id, "label": f"S{n}"})
                sections.append(prompts.STRATEGY_HEADING + "\n" + "\n".join(lines))
        if "hypotheses" in include:
            here = self.graph.hypotheses_in(world)[-self.config.max_hypotheses :]
            if here:
                sections.append(
                    prompts.SAME_WORLD_HEADING
                    + "\n"
                    + "\n".join(_hypothesis_line(h, self.graph) for h in here)
                )
                ids += [h.id for h in here]
                details += [{"kind": "hypothesis", "id": h.id, "scope": "same world"} for h in here]
            if self.config.other_worlds == "scoped":
                elsewhere = self.graph.hypotheses_elsewhere(world)[-self.config.max_hypotheses :]
                if elsewhere:
                    sections.append(
                        prompts.ELSEWHERE_HEADING
                        + "\n"
                        + "\n".join(_hypothesis_line(h, self.graph, scoped=True) for h in elsewhere)
                    )
                    ids += [h.id for h in elsewhere]
                    details += [
                        {"kind": "hypothesis", "id": h.id, "scope": "other world"}
                        for h in elsewhere
                    ]
        if "evidence" in include:
            measured = self.graph.evidence_in(world)[-self.config.max_evidence :]
            if measured:
                sections.append(
                    prompts.EVIDENCE_HEADING + "\n" + "\n".join(f"- {e.text}" for e in measured)
                )
                ids += [e.id for e in measured]
                details += [{"kind": "evidence", "id": e.id} for e in measured]
        if not sections:
            return Retrieval()
        text = prompts.MEMORY_HEADING + "\n\n" + "\n\n".join(sections)
        if mode == "placebo":
            return Retrieval(
                block=_block(prompts.MEMORY_HEADING + "\n\n" + _placebo(len(text)), []),
                details=[{"kind": "placebo", "replaces": len(ids), "chars": len(text)}],
            )
        return Retrieval(block=_block(text, ids), details=details)

    def _answers(self, world: dict[str, Any]) -> Retrieval:
        """The foil: what was found in worlds of this kind, as plain facts."""
        found = [
            h
            for h in self.graph.hypotheses_in(world) + self.graph.hypotheses_elsewhere(world)
            if h.status == "supported"
        ][-self.config.max_hypotheses :]
        if not found:
            return Retrieval()
        text = (
            prompts.MEMORY_HEADING
            + "\n\n"
            + prompts.ANSWERS_HEADING
            + "\n"
            + "\n".join(f"- {h.statement}" for h in found)
        )
        return Retrieval(
            block=_block(text, [h.id for h in found]),
            details=[{"kind": "answer", "id": h.id} for h in found],
        )

    # ------------------------------------------------------------------ learning

    def learn_single(
        self, env: TextEnv, task: Task, query: str, traj: Trajectory, verdict: Verdict
    ) -> Learned:
        shown = [
            {"label": d["label"], **_strategy_fields(self.graph.strategies[d["id"]])}
            for d in traj.meta.get("retrieval", [])
            if d.get("kind") == "strategy" and d.get("id") in self.graph.strategies
        ]
        review = self.config.review and bool(shown) and self.config.mode == "full"
        ending = (
            f"{traj.final_observation.splitlines()[0] if traj.final_observation else ''}\n"
            f"Your own verdict: the attempt was a {verdict.label} ({verdict.thoughts[:400]})."
        )
        if traj.steps and traj.steps[-1].result:
            ending = f"Last result: {traj.steps[-1].result[:400]}\n" + ending
        response = self.llm.complete(
            LLMRequest(
                system=prompts.extraction_system(review),
                messages=[
                    user(
                        prompts.extraction_input(
                            query,
                            render_episode(traj, self.config.max_trajectory_chars),
                            agent_notes(traj),
                            ending,
                            shown if review else None,
                        )
                    )
                ],
                purpose="extract_investigation",
                max_tokens=self.config.extraction_max_tokens,
                temperature=self.config.extraction_temperature,
                meta={"trajectory": traj.id},
            )
        )
        try:
            parsed = extract_json_object(response.text)
        except ValueError:
            parsed = {}
        world = world_of(task)
        created = self._add(parsed, world, traj, verdict, response.call_id)
        if review:
            created += self._review(parsed.get("strategy_review") or [], shown, traj, world)
        self.graph.episodes.append(
            {
                "episode": traj.id,
                "world": world,
                "verdict": verdict.label,
                "created": created,
                "llm_call_id": response.call_id,
                "parsed": bool(parsed),
            }
        )
        self.graph.save()
        return Learned(item_ids=created)

    def _add(
        self,
        parsed: dict[str, Any],
        world: dict[str, Any],
        traj: Trajectory,
        verdict: Verdict,
        call_id: str | None,
    ) -> list[str]:
        created: list[str] = []
        evidence_ids: list[str] = []
        for item in _dicts(parsed.get("evidence")):
            text = str(item.get("text", "")).strip()
            if not text:
                evidence_ids.append("")
                continue
            step = item.get("step")
            ev = Evidence(
                text=text[:400],
                world=world,
                episode=traj.id,
                step=int(step) if isinstance(step, (int, float)) else None,
            )
            self.graph.evidence[ev.id] = ev
            evidence_ids.append(ev.id)
            created.append(ev.id)

        def refs(values: Any) -> list[str]:
            out = []
            for value in values if isinstance(values, list) else []:
                if (
                    isinstance(value, int)
                    and 0 <= value < len(evidence_ids)
                    and evidence_ids[value]
                ):
                    out.append(evidence_ids[value])
            return out

        for item in _dicts(parsed.get("hypotheses")):
            statement = str(item.get("statement", "")).strip()
            if not statement:
                continue
            status = str(item.get("status", "open")).lower()
            hyp = Hypothesis(
                statement=statement[:400],
                conditions=str(item.get("conditions", "")).strip()[:300],
                status=status if status in STATUSES else "open",
                world=world,
                episode=traj.id,
                supported_by=refs(item.get("supported_by")),
                contradicted_by=refs(item.get("contradicted_by")),
            )
            self.graph.hypotheses[hyp.id] = hyp
            created.append(hyp.id)

        for item in _dicts(parsed.get("strategies")):
            statement = str(item.get("statement", "")).strip()
            if not statement:
                continue
            strategy = Strategy(
                statement=statement[:400],
                applies_when=str(item.get("applies_when", "")).strip()[:300],
                test=str(item.get("test", "")).strip()[:300],
                basis=str(item.get("basis", "")).strip()[:300],
                derived_from=[traj.id],
                worlds=[world_key(world)],
            )
            self.graph.strategies[strategy.id] = strategy
            created.append(strategy.id)

        if self.store is not None:
            for node_id in created:
                kind = node_id.split("_", 1)[0]
                node = (
                    self.graph.evidence.get(node_id)
                    or self.graph.hypotheses.get(node_id)
                    or self.graph.strategies.get(node_id)
                )
                label = getattr(node, "text", None) or getattr(node, "statement", "")
                self.store.add_node(
                    node_id,
                    {"ev": "evidence", "hyp": "hypothesis", "str": "strategy"}[kind],
                    label=str(label)[:200],
                    data={"world": world, "verdict": verdict.label},
                )
                self.store.link(node_id, WAS_DERIVED_FROM, traj.id)
                if call_id:
                    self.store.link(node_id, WAS_GENERATED_BY, call_id)
        return created

    def _review(
        self,
        reviews: list[Any],
        shown: list[dict[str, Any]],
        traj: Trajectory,
        world: dict[str, Any],
    ) -> list[str]:
        by_label = {s["label"]: s for s in shown}
        created: list[str] = []
        for item in _dicts(reviews):
            entry = by_label.get(str(item.get("id", "")))
            if entry is None:
                continue
            strategy = self.graph.strategies[entry["id"]]
            used = bool(item.get("used"))
            outcome = str(item.get("outcome", "")).lower()
            strategy.record.append(
                {
                    "episode": traj.id,
                    "world": world_key(world),
                    "used": used,
                    "outcome": outcome,
                    "reason": str(item.get("reason", ""))[:300],
                }
            )
            if not used:
                continue
            strategy.uses += 1
            if outcome == "helped":
                strategy.helped += 1
            elif outcome in ("did not help", "did_not_help", "not helped"):
                strategy.did_not_help += 1
                revised = str(item.get("revised_statement") or "").strip()
                narrower = str(item.get("revised_applies_when") or "").strip()
                if revised and narrower:
                    replacement = Strategy(
                        statement=revised[:400],
                        applies_when=narrower[:300],
                        test=strategy.test,
                        basis=f"revised after {traj.id}: {str(item.get('reason', ''))[:200]}",
                        derived_from=[*strategy.derived_from, traj.id],
                        worlds=sorted({*strategy.worlds, world_key(world)}),
                        revised_from=strategy.id,
                    )
                    strategy.status = "replaced"
                    self.graph.strategies[replacement.id] = replacement
                    created.append(replacement.id)
        return created

    def stats(self) -> dict[str, Any]:
        return {
            "kind": "investigation_memory",
            "mode": self.config.mode,
            "include": list(self.config.include),
            "embedder": self.embedder.name,
            **self.graph.counts(),
        }


def _dicts(values: Any) -> list[dict[str, Any]]:
    return [v for v in values if isinstance(v, dict)] if isinstance(values, list) else []


def _strategy_fields(s: Strategy) -> dict[str, Any]:
    return {"id": s.id, "statement": s.statement, "applies_when": s.applies_when}


def _hypothesis_line(h: Hypothesis, graph: InvestigationGraph, scoped: bool = False) -> str:
    line = f"- {h.statement} [{h.status}]"
    if h.conditions:
        line += f" Observed under: {h.conditions}."
    support = [graph.evidence[e].text for e in h.supported_by if e in graph.evidence][:2]
    against = [graph.evidence[e].text for e in h.contradicted_by if e in graph.evidence][:2]
    if support:
        line += " Evidence for: " + "; ".join(support) + "."
    if against:
        line += " Evidence against: " + "; ".join(against) + "."
    if scoped:
        line += f" (Another world of this kind: {world_key(h.world).split('/seed=')[0]}.)"
    return line


def _block(text: str, ids: Sequence[str]) -> Any:
    from ...agents.base import MemoryBlock

    return MemoryBlock(text=text, item_ids=list(ids))


def _placebo(chars: int) -> str:
    sentences = list(prompts.PLACEBO_SENTENCES)
    lines: list[str] = []
    total = 0
    i = 0
    while total < chars and i < 4 * len(sentences):
        sentence = sentences[i % len(sentences)]
        lines.append(f"- {sentence}")
        total += len(sentence) + 3
        i += 1
    return "\n".join(lines)


def build(
    config: InvestigationMemoryConfig,
    llm: Any,
    *,
    path: Any = None,
    embedder: Embedder | None = None,
    store: ProvenanceStore | None = None,
) -> tuple[InvestigationMemory, Any]:
    """The memory and the judge that labels episodes for it."""
    from pathlib import Path

    from ..reasoningbank import LLMJudge
    from ..stream import EnvJudge

    if path is not None and str(path).endswith("bank.jsonl"):
        path = Path(path).with_name("investigation_memory.json")
    memory = InvestigationMemory(config, llm, path=path, embedder=embedder, store=store)
    judge = None
    if memory.learns:
        judge = EnvJudge() if config.judge == "env" else LLMJudge(llm)
    return memory, judge
