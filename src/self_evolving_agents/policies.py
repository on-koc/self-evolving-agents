"""Executable rule policies.

A :class:`RulePolicy` is an ordered list of ``if condition then action`` rules over
an environment's named features, with a default action. It is plain data: it
serialises to JSON, can be written by a person or a language model, is evaluated
without ``eval``, and gives identical decisions every time. That repeatability is
what makes a strategy testable: the same policy can be rerun on matched seeds with
one thing changed.

Thresholds may be literals or references to named parameters (``"$charge_below"``),
so that a claim can be about a single knob of an otherwise fixed policy.

Condition grammar::

    {"battery": {"<": 0.25}}                       one comparison
    {"battery": {"<": "$charge_below"}}            against a parameter
    {"battery": {"<": 0.25}, "in_eclipse": {"==": 0}}   several keys are ANDed
    {"all": [cond, ...]}   {"any": [cond, ...]}   {"not": cond}
"""

from __future__ import annotations

import copy
import operator
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .types import stable_hash

_OPS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


class PolicyError(ValueError):
    """The policy is malformed or refers to unknown features, parameters or actions."""


def _resolve(value: Any, params: Mapping[str, float]) -> float:
    if isinstance(value, str):
        if not value.startswith("$"):
            raise PolicyError(f"threshold {value!r} must be a number or a $parameter")
        name = value[1:]
        if name not in params:
            raise PolicyError(f"unknown parameter ${name}")
        return float(params[name])
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"threshold {value!r} must be a number or a $parameter")
    return float(value)


def evaluate(condition: Any, features: Mapping[str, float], params: Mapping[str, float]) -> bool:
    """Evaluate a condition tree against a feature dictionary."""
    if not isinstance(condition, dict) or not condition:
        raise PolicyError(f"condition must be a non-empty object, got {condition!r}")
    result = True
    for key, value in condition.items():
        if key == "all":
            ok = all(evaluate(c, features, params) for c in _as_list(value, key))
        elif key == "any":
            ok = any(evaluate(c, features, params) for c in _as_list(value, key))
        elif key == "not":
            ok = not evaluate(value, features, params)
        else:
            if key not in features:
                raise PolicyError(f"unknown feature {key!r}")
            if not isinstance(value, dict) or not value:
                raise PolicyError(f"feature {key!r} needs comparisons like {{'<': 0.5}}")
            ok = True
            for op, threshold in value.items():
                if op not in _OPS:
                    raise PolicyError(f"unknown operator {op!r}")
                ok = ok and _OPS[op](float(features[key]), _resolve(threshold, params))
        result = result and ok
    return result


def _as_list(value: Any, key: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise PolicyError(f"'{key}' needs a non-empty list of conditions")
    return value


def _features_in(condition: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(condition, dict):
        for key, value in condition.items():
            if key in ("all", "any"):
                for c in value if isinstance(value, list) else []:
                    found |= _features_in(c)
            elif key == "not":
                found |= _features_in(value)
            else:
                found.add(key)
    return found


def _params_in(condition: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(condition, dict):
        for value in condition.values():
            found |= _params_in(value)
    elif isinstance(condition, list):
        for value in condition:
            found |= _params_in(value)
    elif isinstance(condition, str) and condition.startswith("$"):
        found.add(condition[1:])
    return found


@dataclass
class RulePolicy:
    """First matching rule wins; ``default`` applies when none match."""

    rules: list[dict[str, Any]]
    default: str
    params: dict[str, float] = field(default_factory=dict)
    name: str = "policy"

    def act(self, features: Mapping[str, float]) -> str:
        for rule in self.rules:
            if evaluate(rule["if"], features, self.params):
                return rule["do"]
        return self.default

    def explain(self, features: Mapping[str, float]) -> tuple[str, int | None]:
        """Return ``(action, index of the rule that fired)``; index is ``None`` for the default."""
        for i, rule in enumerate(self.rules):
            if evaluate(rule["if"], features, self.params):
                return rule["do"], i
        return self.default, None

    def with_params(self, **overrides: float) -> RulePolicy:
        """A copy with some parameters changed. Unknown names are an error."""
        unknown = set(overrides) - set(self.params)
        if unknown:
            raise PolicyError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
        return RulePolicy(
            rules=copy.deepcopy(self.rules),
            default=self.default,
            params={**self.params, **{k: float(v) for k, v in overrides.items()}},
            name=self.name,
        )

    def validate(self, feature_names: list[str], action_names: list[str]) -> None:
        """Check structure, names and that every referenced parameter is defined."""
        if self.default not in action_names:
            raise PolicyError(f"default action {self.default!r} is not one of {action_names}")
        if not isinstance(self.rules, list):
            raise PolicyError("rules must be a list")
        probe = {name: 0.0 for name in feature_names}
        for i, rule in enumerate(self.rules):
            if not isinstance(rule, dict) or set(rule) - {"if", "do", "note"} or "if" not in rule:
                raise PolicyError(f"rule {i} must be an object with 'if' and 'do'")
            if rule.get("do") not in action_names:
                raise PolicyError(
                    f"rule {i}: action {rule.get('do')!r} is not one of {action_names}"
                )
            unknown = _features_in(rule["if"]) - set(feature_names)
            if unknown:
                raise PolicyError(f"rule {i}: unknown feature(s) {', '.join(sorted(unknown))}")
            missing = _params_in(rule["if"]) - set(self.params)
            if missing:
                raise PolicyError(f"rule {i}: undefined parameter(s) {', '.join(sorted(missing))}")
            evaluate(rule["if"], probe, self.params)  # raises on any remaining malformation

    @property
    def fingerprint(self) -> str:
        """Identity of the decision rule, independent of its display name."""
        return stable_hash({"rules": self.rules, "default": self.default, "params": self.params})

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rules": copy.deepcopy(self.rules),
            "default": self.default,
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> RulePolicy:
        if "rules" not in d or "default" not in d:
            raise PolicyError("a policy needs 'rules' and 'default'")
        return cls(
            rules=copy.deepcopy(list(d["rules"])),
            default=str(d["default"]),
            params={k: float(v) for k, v in dict(d.get("params") or {}).items()},
            name=str(d.get("name", "policy")),
        )

    def describe(self) -> str:
        """Readable rendering for prompts and reports."""
        lines = [f"Policy '{self.name}' (first matching rule wins):"]
        for i, rule in enumerate(self.rules, 1):
            lines.append(f"  {i}. if {_describe(rule['if'], self.params)} -> {rule['do']}")
        lines.append(f"  otherwise -> {self.default}")
        return "\n".join(lines)


def _describe(condition: Any, params: Mapping[str, float]) -> str:
    parts = []
    for key, value in condition.items():
        if key in ("all", "any"):
            joiner = " and " if key == "all" else " or "
            parts.append("(" + joiner.join(_describe(c, params) for c in value) + ")")
        elif key == "not":
            parts.append(f"not ({_describe(value, params)})")
        else:
            for op, threshold in value.items():
                shown = threshold
                if isinstance(threshold, str) and threshold[1:] in params:
                    shown = f"{params[threshold[1:]]:g} [{threshold}]"
                parts.append(f"{key} {op} {shown}")
    return " and ".join(parts)


# --------------------------------------------------------------------------- scanning

#: Parameters of the reference scanning policy and what each one controls.
SCAN_POLICY_PARAMS: dict[str, str] = {
    "desat_above": "unload the wheels when the fastest one exceeds this fraction of its limit",
    "charge_below": "switch to charging when the battery falls below this fraction",
    "charge_until": "once charging in sunlight, keep charging up to this fraction",
    "precharge_window_s": "start topping up this many seconds before an eclipse begins",
    "precharge_below": "... but only if the battery is below this fraction",
    "downlink_above": "downlink during a pass when the buffer is fuller than this fraction",
    "storage_full": "stop scanning and wait when the buffer is fuller than this fraction",
}


def scanning_policy(name: str = "reference", **params: float) -> RulePolicy:
    """The reference rule policy for the nadir-scanning task.

    One fixed rule structure with seven thresholds. The defaults are a plain,
    untuned starting point; which values are *good* depends on the operating regime,
    and finding that out is what the experiments are for.
    """
    defaults = {
        "desat_above": 0.6,
        "charge_below": 0.25,
        "charge_until": 0.25,
        "precharge_window_s": 0.0,
        "precharge_below": 0.0,
        "downlink_above": 0.05,
        "storage_full": 0.98,
    }
    unknown = set(params) - set(defaults)
    if unknown:
        raise PolicyError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
    rules = [
        {"if": {"wheel_speed": {">": "$desat_above"}}, "do": "desat"},
        {"if": {"battery": {"<": "$charge_below"}}, "do": "charge"},
        {
            "if": {
                "prev_charge": {"==": 1},
                "in_eclipse": {"==": 0},
                "battery": {"<": "$charge_until"},
            },
            "do": "charge",
        },
        {
            "if": {
                "in_eclipse": {"==": 0},
                "eclipse_start_s": {"<": "$precharge_window_s"},
                "battery": {"<": "$precharge_below"},
            },
            "do": "charge",
        },
        {"if": {"gs_in_view": {"==": 1}, "storage": {">": "$downlink_above"}}, "do": "downlink"},
        {"if": {"storage": {">": "$storage_full"}}, "do": "charge"},
    ]
    return RulePolicy(rules=rules, default="scan", params={**defaults, **params}, name=name)


def always(action: str, name: str | None = None) -> RulePolicy:
    """A policy that takes the same action at every step."""
    return RulePolicy(rules=[], default=action, params={}, name=name or f"always-{action}")
