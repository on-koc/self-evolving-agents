"""Self-evolving agents: reasoning memory and simulation-tested claim revision.

Two layers live here:

* ``reasoningbank`` adapts ReasoningBank (Ouyang et al., ICLR 2026) to simulation
  environments: retrieve memory items, act, judge, extract new items from both
  successful and failed trajectories, and consolidate.
* ``claims`` + ``experiments`` go beyond it: conditional claims with applicability
  regions, backed by matched-seed controlled experiments, and revised by evidence.

Everything that happens is written to a provenance store so that every memory item
and claim can be traced back to the trajectories and experiments it came from.
"""

__version__ = "0.1.0"
