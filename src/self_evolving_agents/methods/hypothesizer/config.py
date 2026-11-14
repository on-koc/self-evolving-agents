"""Configuration of the Hypothesizer baseline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HypothesizerConfig:
    #: ``"json"``: the API's observation, as in the original. ``"text"``: the compact
    #: rendering, for models with a small context (a deviation; see the method's page).
    observation: str = "json"
    #: Decoding temperature of every call (0.1 in the original).
    temperature: float = 0.1
    #: Steps between consolidations of the knowledge store.
    consolidate_every: int = 10
    #: Show the dialog in the dialog addition (the original overwrites it; off as released).
    fixed_dialog_prompt: bool = False
    #: Judge episodes anyway, to measure judge agreement: ``"none"``, ``"llm"`` or ``"env"``.
    judge: str = "none"

    def __post_init__(self) -> None:
        if self.observation not in ("json", "text"):
            raise ValueError("observation must be 'json' or 'text'")
        if self.judge not in ("none", "llm", "env"):
            raise ValueError("judge must be 'none', 'llm' or 'env'")

    def agent_options(self) -> dict[str, object]:
        return {
            "observation": self.observation,
            "temperature": self.temperature,
            "consolidate_every": self.consolidate_every,
            "fixed_dialog_prompt": self.fixed_dialog_prompt,
        }
