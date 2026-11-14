"""DiscoveryWorld's Hypothesizer agent: the benchmark's own baseline, ported faithfully.

It keeps a store of measurements and hypotheses within an episode and starts every
episode with an empty one. As a method it is that agent with no memory across
episodes; as an agent (``--agent hypothesizer``) it can be paired with a memory
method, which is how the DiscoveryWorld experiment compares memories on one actor.
"""

from .agent import HypothesizerAgent, count_tokens, extract_json
from .config import HypothesizerConfig

__all__ = ["HypothesizerAgent", "HypothesizerConfig", "count_tokens", "extract_json"]
