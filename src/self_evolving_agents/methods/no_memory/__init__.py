"""No memory: the agent meets every task as if it were the first. The reference point.

This is the paper's "No Memory" (vanilla) baseline. There is nothing to implement:
the stream loop's default memory retrieves nothing and learns nothing. See
``docs/methods/no_memory.md``.
"""

from ..stream import Memory as NoMemory

__all__ = ["NoMemory"]
