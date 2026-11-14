"""Claims tested in simulation, shown to a language-model agent as memory.

The bridge between the claim graph and the ReasoningBank loop. Not part of the
published method and not evaluated with a language model. See
``docs/methods/claim_memory.md``.
"""

from .method import ClaimMemory, ClaimMemoryConfig
from .render import SOURCE_CLAIM, claims_as_memory

__all__ = ["SOURCE_CLAIM", "ClaimMemory", "ClaimMemoryConfig", "claims_as_memory"]
