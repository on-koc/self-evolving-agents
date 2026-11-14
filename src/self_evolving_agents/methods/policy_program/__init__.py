"""The model writes an executable rule policy once per episode instead of acting step by step.

An adaptation of the acting step, not part of the published method. See
``docs/methods/policy_program.md``.
"""

from .agent import PolicyProgramAgent
from .prompts import MEMORY_INSTRUCTION_POLICY, POLICY_FORMAT

__all__ = ["MEMORY_INSTRUCTION_POLICY", "POLICY_FORMAT", "PolicyProgramAgent"]
