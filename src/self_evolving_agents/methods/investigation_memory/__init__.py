"""Investigation memory: evidence, conditional hypotheses and transferable strategies.

Built for the DiscoveryWorld experiment. Its claim to test is that what transfers
between scientific tasks is how to investigate, not what was found: remembering
which substance removed the rust in one world does not help in a world where another
one does, while remembering how the effective substance was identified might.
"""

from .config import KINDS, MODES, InvestigationMemoryConfig
from .memory import InvestigationMemory, build, render_episode
from .schema import Evidence, Hypothesis, InvestigationGraph, Strategy, world_key, world_of

__all__ = [
    "KINDS",
    "MODES",
    "Evidence",
    "Hypothesis",
    "InvestigationGraph",
    "InvestigationMemory",
    "InvestigationMemoryConfig",
    "Strategy",
    "build",
    "render_episode",
    "world_key",
    "world_of",
]
