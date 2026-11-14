"""DiscoveryWorld's own baseline agents: ReAct, Plan-and-Execute and the random agent.

Faithful ports of the agents released with DiscoveryWorld (``agents/recoma/`` and
``agents/RandomAgent.py``, Apache License 2.0, Allen Institute for AI). DiscoveryWorld's
third baseline, the Hypothesizer, lives in ``methods/hypothesizer`` because it is also
run as a method of its own. ``docs/agents.md`` documents every agent.
"""

from .plan_execute import PlanExecuteAgent
from .random_agent import RandomAgent
from .react import ReActAgent

__all__ = ["PlanExecuteAgent", "RandomAgent", "ReActAgent"]
