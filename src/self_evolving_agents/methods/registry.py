"""The methods of this repository, and how to build each one.

Every method has a name, a folder under ``methods/``, a page under ``docs/methods/``
and a configuration class holding its parameters with their defaults. A method that
runs on a stream of tasks is built with :func:`build_stream`; the claim graph is a
study and is run with ``sea claims study``.

``sea methods`` prints this table.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..agents import Agent, StepwiseAgent
from ..embeddings import Embedder
from ..provenance import ProvenanceStore
from .stream import EnvJudge, Judge, Memory, Scaling, StreamLoop

AGENTS = ("stepwise", "policy_program", "hypothesizer", "react", "plan_execute", "random")

#: Environments of the scanning task, which share its conditions and rule policies.
SCANNING_ENVS = ("bsk-scan", "toy-scan")


@dataclass(frozen=True)
class AgentSpec:
    name: str
    origin: str
    summary: str
    #: Environments the agent can play; ``None`` for any text environment.
    environments: tuple[str, ...] | None = None
    #: Whether a method's memory reaches the agent's prompt.
    reads_memory: bool = True


AGENT_SPECS: dict[str, AgentSpec] = {
    spec.name: spec
    for spec in (
        AgentSpec(
            "stepwise",
            "ReasoningBank paper",
            "one model call per action: task, memory, recent steps and the observation as text",
        ),
        AgentSpec(
            "policy_program",
            "adaptation",
            "one model call per episode writes a rule policy over numeric features, which is run",
            environments=SCANNING_ENVS,
        ),
        AgentSpec(
            "hypothesizer",
            "DiscoveryWorld",
            "acts, then records measurements and hypotheses after every step (two calls per step)",
            environments=("discoveryworld",),
        ),
        AgentSpec(
            "react",
            "DiscoveryWorld",
            "one call per action on the API's JSON observation with the history of actions "
            "and results; SUBMIT ends the episode",
            environments=("discoveryworld",),
        ),
        AgentSpec(
            "plan_execute",
            "DiscoveryWorld",
            "a planner writes one step at a time; a ReAct executor carries each step out "
            "and reports its result",
            environments=("discoveryworld",),
        ),
        AgentSpec(
            "random",
            "DiscoveryWorld",
            "random actions on random objects within reach; no model",
            environments=("discoveryworld",),
            reads_memory=False,
        ),
    )
}

#: The agent a method uses unless another is named.
DEFAULT_AGENT = {
    "policy_program": "policy_program",
    "hypothesizer": "hypothesizer",
    "investigation_memory": "hypothesizer",
}
#: Methods that only work with one agent.
FIXED_AGENT = {"policy_program": "policy_program", "hypothesizer": "hypothesizer"}


def default_agent(method: str) -> str:
    return DEFAULT_AGENT.get(method, "stepwise")


def resolve_agent(method: str, agent: str | None) -> str:
    """The agent a method runs with; an error for an agent the method cannot use."""
    if agent is None:
        return default_agent(method)
    if agent not in AGENTS:
        raise ValueError(f"unknown agent {agent!r}; one of {', '.join(AGENTS)}")
    fixed = FIXED_AGENT.get(method)
    if fixed and agent != fixed:
        raise ValueError(
            f"the {method} method is its own agent ({fixed}); it cannot run with the {agent} "
            f"agent. To give the {agent} agent no memory, use the no_memory method"
        )
    if not AGENT_SPECS[agent].reads_memory and method != "no_memory":
        raise ValueError(
            f"the {agent} agent reads no memory, so {method} would change nothing; run it "
            "with the no_memory method"
        )
    return agent


def protocol_agent(protocol: dict[str, Any], arm: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """The agent and agent options of one arm of a protocol.

    An arm may name its agent; otherwise the protocol's agent applies, except to a
    method that is its own agent. The protocol's agent options apply to arms that use
    the protocol's agent (they are constructor options of that agent); an arm's own
    options are added on top.
    """
    method = arm["method"]
    if arm.get("agent"):
        agent = arm["agent"]
    elif method in FIXED_AGENT:
        agent = FIXED_AGENT[method]
    else:
        agent = protocol.get("agent")
    resolved = resolve_agent(method, agent)
    options: dict[str, Any] = {}
    if resolved == protocol.get("agent"):
        options.update(protocol.get("agent_options") or {})
    options.update(arm.get("agent_options") or {})
    return resolved, options


def check_combination(
    method: str, agent: str | None, env_ids: set[str], options: dict[str, Any] | None = None
) -> str:
    """Refuse, before anything is spent, a method, agent and environment that cannot work.

    Returns the resolved agent.
    """
    resolved = resolve_agent(method, agent)
    allowed = AGENT_SPECS[resolved].environments
    for env_id in sorted(env_ids):
        if allowed is not None and env_id not in allowed:
            if resolved == "policy_program":
                raise ValueError(
                    f"the policy_program agent writes rule policies over named numeric "
                    f"features, which {env_id} does not expose; it runs on "
                    f"{', '.join(allowed)}"
                )
            raise ValueError(f"the {resolved} agent plays {', '.join(allowed)}, not {env_id}")
    if method == "claim_memory":
        claims = (options or {}).get("claims")
        study_env = "a scanning environment"
        if claims and (Path(claims) / "config.json").exists():
            domain = json.loads((Path(claims) / "config.json").read_text()).get("domain") or {}
            study_env = domain.get("env_id") or study_env
        for env_id in sorted(env_ids):
            if env_id not in SCANNING_ENVS:
                raise ValueError(
                    f"claim_memory shows claims about the parameters of the scanning task's "
                    f"rule policies (tested on {study_env}); they say nothing about {env_id}. "
                    "Claim studies exist only for the scanning environments"
                )
    return resolved


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
            "hypothesizer",
            "DiscoveryWorld Hypothesizer",
            "baseline (DiscoveryWorld)",
            "DiscoveryWorld's own agent: acts, then records measurements and hypotheses with "
            "a status after every step, within one episode. No memory across episodes.",
            _NOT_RUN,
        ),
        MethodSpec(
            "investigation_memory",
            "Investigation memory",
            "extension",
            "Memory across tasks in three kinds: evidence from one world, hypotheses with the "
            "conditions they were observed under, and investigation strategies meant to "
            "transfer, linked by support, contradiction and use.",
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
    if method == "hypothesizer":
        from .hypothesizer import HypothesizerConfig

        return HypothesizerConfig
    if method == "investigation_memory":
        from .investigation_memory import InvestigationMemoryConfig

        return InvestigationMemoryConfig
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
    if kind == "hypothesizer":
        from .hypothesizer import HypothesizerAgent

        return HypothesizerAgent(llm, **options)
    if kind == "react":
        from ..agents.discoveryworld import ReActAgent

        return ReActAgent(llm, **options)
    if kind == "plan_execute":
        from ..agents.discoveryworld import PlanExecuteAgent

        return PlanExecuteAgent(llm, **options)
    if kind == "random":
        from ..agents.discoveryworld import RandomAgent

        return RandomAgent(llm, **options)
    raise ValueError(f"agent must be one of {AGENTS}")


def build_stream(
    method: str,
    options: dict[str, Any] | None = None,
    *,
    llm: Any,
    agent: str | None = None,
    agent_options: dict[str, Any] | None = None,
    bank_path: str | Path | None = None,
    embedder: Embedder | None = None,
    store: ProvenanceStore | None = None,
    on_record: Callable[[Any], None] | None = None,
    store_steps: bool = True,
    learn: bool = True,
) -> Built:
    """Wire up one stream method.

    Args:
        method: a name from :data:`METHODS` with ``runner == "stream"``.
        options: overrides of the method's configuration defaults.
        llm: the model, used by the agent and by every other component of the
            method (the paper uses one backbone throughout).
        agent: one of :data:`AGENTS`, or ``None`` for the method's default
            (:func:`default_agent`). The ``policy_program`` and ``hypothesizer``
            methods are their own agents and refuse any other.
        agent_options: constructor options of the agent (history window, ...).
        bank_path: where a learning memory keeps its bank.
        embedder: embeds queries for retrieval.
        learn: ``False`` freezes the memory (it is consulted, not changed).
    """
    config = make_config(method, options)
    agent_options = dict(agent_options or {})
    agent = resolve_agent(method, agent)
    if method == "hypothesizer":
        agent_options = {**config.agent_options(), **agent_options}
    policy_agent = agent == "policy_program"
    the_agent = _agent(agent, llm, agent_options)

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

    if method in ("no_memory", "hypothesizer"):
        if config.judge == "env":
            judge = EnvJudge()
        elif config.judge == "llm":
            from .reasoningbank import LLMJudge

            judge = LLMJudge(llm)

    elif method == "investigation_memory":
        from .investigation_memory import build as build_investigation

        memory, judge = build_investigation(
            config, llm, path=bank_path, embedder=embedder, store=store
        )

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
        learn=learn,
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
        "learn": learn,
    }
    return Built(loop, method, config, the_agent, memory, describe)
