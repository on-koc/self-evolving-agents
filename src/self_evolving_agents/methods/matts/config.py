"""Parameters of memory-aware test-time scaling."""

from __future__ import annotations

from dataclasses import dataclass

from ..reasoningbank.method import ReasoningBankConfig
from .scaling import SCALINGS


@dataclass
class MattsConfig(ReasoningBankConfig):
    """The baseline's parameters plus those of scaling.

    The paper's headline configuration is parallel scaling with k = 5 (its Table 1);
    its Figure 4 varies k from 1 to 5.
    """

    #: ``"parallel"`` (MaTTS, published), ``"vanilla"`` (no aggregation, published
    #: control) or ``"restart"`` (adaptation standing in for sequential scaling).
    scaling: str = "parallel"
    #: Scaling factor: attempts per task. 1 is no scaling.
    scaling_k: int = 5
    #: ``False`` scales without any memory: the paper's "MaTTS w/o memory" control.
    memory: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.scaling not in SCALINGS:
            raise ValueError(f"scaling must be one of {tuple(SCALINGS)}")
        if self.scaling_k < 1:
            raise ValueError("scaling_k must be at least 1")
