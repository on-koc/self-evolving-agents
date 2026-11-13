"""The methods of this repository, and how to build each one.

Every method has a name, a folder under ``methods/``, a page under ``docs/methods/``
and a configuration class holding its parameters with their defaults. A method that
runs on a stream of tasks is built with :func:`build_stream`; the claim graph is a
study and is run with ``sea claims study``.

``sea methods`` prints this table.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..agents import Agent, StepwiseAgent
from ..embeddings import Embedder
from ..provenance import ProvenanceStore
from .stream import EnvJudge, Judge, Memory, Scaling, StreamLoop

AGENTS = ("stepwise", "policy_program")


@dataclass(frozen=True)
class MethodSpec:
    name: str
    title: str
    #: ``"paper"``: part of the published ReasoningBank work. ``"reference point"``:
    #: the comparison baseline. ``"adaptation"`` / ``"extension"``: ours.
    origin: str
    summary: str
    #: What evidence exists for it in this repository.
    evidence: str
    needs_model: bool = True
    #: ``"stream"`` (``sea run``) or ``"study"`` (``sea claims study``).
    runner: str = "stream"

    @property
    def doc(self) -> str:
        return f"docs/methods/{self.name}.md"

    @property
    def package(self) -> str:
        return f"self_evolving_agents.methods.{self.name}"


_NOT_RUN = "verified for correctness with scripted stand-ins; never run with a language model"

METHODS: dict[str, MethodSpec] = {
    spec.name: spec
    for spec in (
        MethodSpec(
            "no_memory",
            "No memory",
            "reference point",
            "The agent meets every task as if it were the first. The paper's vanilla baseline.",
            _NOT_RUN,
        ),
        MethodSpec(
            "reasoningbank",
            "ReasoningBank",
            "paper",
            "Strategy-level memory items distilled from the agent's own judged successes and "
            "failures, retrieved by query similarity, consolidated by appending.",
            _NOT_RUN,
        ),
        MethodSpec(
            "matts",
            "Memory-aware test-time scaling",
            "paper",
            "Several attempts per task: parallel self-contrast and no-aggregation as published; "
            "a restart variant in place of the paper's sequential scaling.",
            _NOT_RUN,
        ),
        MethodSpec(
            "conditioned_retrieval",
            "Condition-aware ReasoningBank",
            "adaptation",
            "Retrieval that weighs the similarity of operating conditions and ranks single "
            "items; extraction that asks for the conditions an insight was observed under.",
            _NOT_RUN,
        ),
        MethodSpec(
            "policy_program",
            "Policy-writing agent",
            "adaptation",
            "The model writes one executable rule policy per episode instead of acting step by "
            "step. One call per episode, and a strategy that can be rerun.",
            _NOT_RUN,
        ),
        MethodSpec(
            "claim_memory",
            "Claims as memory",
            "extension",
            "The agent is shown claims that were tested in simulation and apply under its "
            "task's conditions, with their scope, evidence and counterexamples.",
            _NOT_RUN,
        ),
        MethodSpec(
            "claim_graph",
            "Conditional claim graph",
            "extension",
            "Lessons as conditional claims about an executable policy, tested by matched-seed "
            "experiments chosen from the state of the graph, and revised by the evidence.",
            "evaluated on the Basilisk simulator (no language model): two studies, a "
            "replication and an ablation; see docs/comparison.md",
            needs_model=False,
            runner="study",
        ),
    )
}


# --------------------------------------------------------------------------- configs


@dataclass
class NoMemoryConfig:
    #: Judge the episodes anyway, to measure how well the judge agrees with the
    #: simulator: ``"none"`` (no judge calls), ``"llm"`` or ``"env"``.
    judge: str = "none"

    def __post_init__(self) -> None:
        if self.judge not in ("none", "llm", "env"):
            raise ValueError("judge must be 'none', 'llm' or 'env'")


def config_class(method: str) -> type:
    """The configuration dataclass of a stream method."""
    if method == "no_memory":
        return NoMemoryConfig
    if method == "reasoningbank":
        from .reasoningbank import ReasoningBankConfig

        return ReasoningBankConfig
    if method == "matts":
        from .matts.config import MattsConfig

        return MattsConfig
    if method == "conditioned_retrieval":
        from .conditioned_retrieval import ConditionedConfig

        return ConditionedConfig
    if method == "policy_program":
        from .policy_program.config import PolicyProgramConfig

        return PolicyProgramConfig
    if method == "claim_memory":
        from .claim_memory import ClaimMemoryConfig

        return ClaimMemoryConfig
    if method in METHODS:
        raise ValueError(
            f"{method} is a study, not a stream method; run it with `sea claims study`"
        )
    raise ValueError(f"unknown method {method!r}; one of {sorted(METHODS)}")


def make_config(method: str, options: dict[str, Any] | None = None) -> Any:
    """The method's configuration with ``options`` applied. Unknown options are an error."""
    cls = config_class(method)
    known = {f.name for f in dataclasses.fields(cls)}
    unknown = sorted(set(options or {}) - known)
    if unknown:
        raise ValueError(
            f"{method} has no option {', '.join(unknown)}; its options are {', '.join(sorted(known))}"
        )
    return cls(**(options or {}))


def defaults(method: str) -> dict[str, Any]:
    return dataclasses.asdict(make_config(method))


# --------------------------------------------------------------------------- building


@dataclass
class Built:
    """A stream method ready to run, and what it was built from."""

    loop: StreamLoop
    method: str
    config: Any
    agent: Agent
    memory: Memory
    describe: dict[str, Any] = field(default_factory=dict)


def _agent(kind: str, llm: Any, options: dict[str, Any]) -> Agent:
    if kind == "stepwise":
        return StepwiseAgent(llm, **options)
    if kind == "policy_program":
        from .policy_program import PolicyProgramAgent

        return PolicyProgramAgent(llm, **options)
    raise ValueError(f"agent must be one of {AGENTS}")


def build_stream(
    method: str,
    options: dict[str, Any] | None = None,
    *,
    llm: Any,
    agent: str = "stepwise",
    agent_options: dict[str, Any] | None = None,
    bank_path: str | Path | None = None,
    embedder: Embedder | None = None,
    store: ProvenanceStore | None = None,
    on_record: Callable[[Any], None] | None = None,
    store_steps: bool = True,
) -> Built:
    """Wire up one stream method.

    Args:
        method: a name from :data:`METHODS` with ``runner == "stream"``.
        options: overrides of the method's configuration defaults.
        llm: the model, used by the agent and by every other component of the
            method (the paper uses one backbone throughout).
        agent: ``"stepwise"`` (the paper's) or ``"policy_program"``. The
            ``policy_program`` method always uses the latter.
        agent_options: constructor options of the agent (history window, ...).
        bank_path: where a learning memory keeps its bank.
        embedder: embeds queries for retrieval.
    """
    config = make_config(method, options)
    if method == "policy_program":
        agent = "policy_program"
    policy_agent = agent == "policy_program"
    the_agent = _agent(agent, llm, dict(agent_options or {}))

    # An agent that writes a policy gives no step-by-step reasoning, so whatever
    # memory it is paired with has to show the extractor the observations instead,
    # and the instruction before the items speaks of a policy, not of steps.
    from .reasoningbank import prompts as published

    instruction = published.MEMORY_INSTRUCTION
    if policy_agent:
        from .policy_program import MEMORY_INSTRUCTION_POLICY

        instruction = MEMORY_INSTRUCTION_POLICY

    memory: Memory = Memory()
    scaling: Scaling = Scaling()
    judge: Judge | None = None

    if method == "no_memory":
        if config.judge == "env":
            judge = EnvJudge()
        elif config.judge == "llm":
            from .reasoningbank import LLMJudge

            judge = LLMJudge(llm)

    elif method in ("reasoningbank", "matts", "policy_program"):
        from .reasoningbank import ReasoningBankConfig
        from .reasoningbank import build as build_reasoningbank

        base = ReasoningBankConfig(
            **{f.name: getattr(config, f.name) for f in dataclasses.fields(ReasoningBankConfig)}
        )
        learning, judge = build_reasoningbank(
            base, llm, bank_path=bank_path, embedder=embedder, store=store, instruction=instruction
        )
        if policy_agent:
            learning.extractor.observations = True
        memory = learning
        if method == "matts":
            from .matts import make_scaling

            scaling = make_scaling(config.scaling, llm, config.scaling_k)
            if not config.memory:
                memory = Memory()

    elif method == "conditioned_retrieval":
        from .conditioned_retrieval import build as build_conditioned

        memory, judge = build_conditioned(
            config,
            llm,
            bank_path=bank_path,
            embedder=embedder,
            store=store,
            instruction=instruction,
        )

    elif method == "claim_memory":
        from .claim_graph.graph import ClaimGraph
        from .claim_memory import ClaimMemory

        graph_path = Path(config.claims) / "graph.json"
        if not config.claims or not graph_path.exists():
            raise ValueError(
                "claim_memory needs claims=<directory of a finished claim study>; "
                f"no graph.json in {config.claims!r}"
            )
        base_memory = None
        if config.with_reasoningbank:
            from .reasoningbank import LLMJudge, ReasoningBankConfig
            from .reasoningbank import build as build_reasoningbank

            base_memory, judge = build_reasoningbank(
                ReasoningBankConfig(),
                llm,
                bank_path=bank_path,
                embedder=embedder,
                store=store,
                instruction=instruction,
            )
            if policy_agent:
                base_memory.extractor.observations = True
        else:
            from .reasoningbank import LLMJudge

            judge = LLMJudge(llm)
        memory = ClaimMemory(
            ClaimGraph(graph_path),
            base=base_memory,
            max_claims=config.max_claims,
            instruction=instruction,
            store=store,
        )

    loop = StreamLoop(
        the_agent,
        memory=memory,
        scaling=scaling,
        judge=judge,
        store=store,
        on_record=on_record,
        store_steps=store_steps,
    )
    describe = {
        "method": method,
        "origin": METHODS[method].origin,
        "config": dataclasses.asdict(config),
        "agent": the_agent.descriptor,
        "memory": memory.name,
        "scaling": {"name": scaling.name, "k": scaling.k},
        "judge": judge.source if judge is not None else "none",
        "embedder": getattr(getattr(memory, "bank", None), "embedder", None)
        and memory.bank.embedder.name,  # type: ignore[attr-defined]
    }
    return Built(loop, method, config, the_agent, memory, describe)
