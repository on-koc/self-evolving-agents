"""The DiscoveryWorld use case: does memory make an agent investigate better?

Research question: can an agent with frozen model weights improve its scientific
investigation strategies across tasks, so that it discovers more efficiently and
predicts better under mechanisms it has not seen?

This package is the experiment, not a method: it runs methods from ``methods/`` on
DiscoveryWorld in an experience phase and frozen transfer phases, grades the agents'
knowledge with DiscoveryWorld's own procedure, measures investigative behaviours,
and reports. See ``docs/discoveryworld.md``.
"""

from .behaviours import BEHAVIOUR_DEFINITIONS, BehaviourCoder, detect
from .experiment import CONDITIONS, episodes, grade_protocol, load_protocol, run_protocol
from .knowledge import KnowledgeScorer, grading_prompt

__all__ = [
    "BEHAVIOUR_DEFINITIONS",
    "CONDITIONS",
    "BehaviourCoder",
    "KnowledgeScorer",
    "detect",
    "episodes",
    "grade_protocol",
    "grading_prompt",
    "load_protocol",
    "run_protocol",
]
