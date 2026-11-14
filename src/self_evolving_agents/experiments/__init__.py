"""Controlled experiments: matched-seed episode batches and paired statistics."""

from .runner import EpisodeCache, EpisodeRunner, EpisodeSpec, default_workers
from .stats import (
    PairedResult,
    TrendResult,
    interaction_compare,
    mean_interval,
    paired_compare,
    trend_test,
)

__all__ = [
    "EpisodeCache",
    "EpisodeRunner",
    "EpisodeSpec",
    "PairedResult",
    "TrendResult",
    "default_workers",
    "interaction_compare",
    "mean_interval",
    "paired_compare",
    "trend_test",
]
