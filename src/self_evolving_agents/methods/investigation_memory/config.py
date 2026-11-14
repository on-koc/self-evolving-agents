"""Configuration of the investigation memory, including the variants the experiment needs."""

from __future__ import annotations

from dataclasses import dataclass, field

KINDS = ("evidence", "hypotheses", "strategies")

#: ``full``: the method. ``answers``: the foil that remembers what was found in earlier
#: worlds as plain facts, without conditions, evidence or strategies. ``placebo``:
#: neutral text of similar length in the same place. ``instructed``: no memory; the
#: five behaviours are prescribed instead (the instruction-following reference).
MODES = ("full", "answers", "placebo", "instructed")


@dataclass
class InvestigationMemoryConfig:
    mode: str = "full"
    #: Kinds of memory shown to the agent. Dropping one at evaluation time, with the
    #: memory frozen, is the lesion test.
    include: list[str] = field(default_factory=lambda: list(KINDS))
    #: Hypotheses from other worlds of the same kind: shown with the conditions they
    #: were observed under (``scoped``) or not at all (``hide``).
    other_worlds: str = "scoped"
    max_strategies: int = 6
    max_hypotheses: int = 6
    max_evidence: int = 8
    #: After each episode, ask whether the strategies that were shown helped.
    review: bool = True
    #: ``llm``: the agent's own verdict, as in ReasoningBank. ``env``: the simulator's,
    #: a control without judge error.
    judge: str = "llm"
    extraction_temperature: float | None = 0.0
    extraction_max_tokens: int = 4000
    #: Characters of the episode shown to the extractor (the middle is cut beyond this).
    max_trajectory_chars: int = 40000

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.include = list(self.include)
        unknown = sorted(set(self.include) - set(KINDS))
        if unknown:
            raise ValueError(f"include may only name {KINDS}, not {unknown}")
        if self.other_worlds not in ("scoped", "hide"):
            raise ValueError("other_worlds must be 'scoped' or 'hide'")
        if self.judge not in ("llm", "env"):
            raise ValueError("judge must be 'llm' or 'env'")
