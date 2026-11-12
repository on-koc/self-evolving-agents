"""Conditional claims, tested in simulation and revised by evidence."""

from .evaluate import composition_check, evaluate_transfer
from .graph import ClaimGraph, partition
from .hypotheses import HypothesisError, LLMProposer, claim_from_spec, load_hypotheses
from .loop import ActiveLoop, LadderProposer, Planner, Proposal
from .policy import assemble_policy, policy_map, recommend
from .schema import Claim, Evidence, Mechanism, Region
from .testing import ABResult, ClaimTester, Domain

__all__ = [
    "ABResult",
    "ActiveLoop",
    "Claim",
    "ClaimGraph",
    "ClaimTester",
    "Domain",
    "Evidence",
    "HypothesisError",
    "LLMProposer",
    "LadderProposer",
    "Mechanism",
    "Planner",
    "Proposal",
    "Region",
    "assemble_policy",
    "claim_from_spec",
    "composition_check",
    "evaluate_transfer",
    "load_hypotheses",
    "partition",
    "policy_map",
    "recommend",
]
