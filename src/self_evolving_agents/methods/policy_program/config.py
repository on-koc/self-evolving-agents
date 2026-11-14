"""Parameters of the policy-writing method."""

from __future__ import annotations

from dataclasses import dataclass

from ..reasoningbank.method import ReasoningBankConfig


@dataclass
class PolicyProgramConfig(ReasoningBankConfig):
    """ReasoningBank's parameters; the agent is what differs.

    The memory is the published one, with one forced change: the extractor is shown
    the policy the agent wrote and each step's observation summary and feedback,
    because a policy-executing agent produces no step-by-step reasoning to learn from.
    """
