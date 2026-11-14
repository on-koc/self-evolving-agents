"""Memory-aware test-time scaling (MaTTS), the second contribution of the ReasoningBank paper.

``parallel`` and ``vanilla`` follow the paper. ``restart`` is an adaptation that stands
in for the paper's sequential scaling, which cannot be run in these environments.
See ``docs/methods/matts.md``.
"""

from .scaling import (
    SCALINGS,
    ParallelScaling,
    RestartScaling,
    VanillaScaling,
    make_scaling,
    select_best,
)

__all__ = [
    "SCALINGS",
    "ParallelScaling",
    "RestartScaling",
    "VanillaScaling",
    "make_scaling",
    "select_best",
]
