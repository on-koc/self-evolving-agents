"""Small helpers for reading structured answers out of model replies."""

from __future__ import annotations

import json
import re
from typing import Any

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any]:
    """Pull the last JSON object out of a model reply (fenced block preferred)."""
    candidates = _JSON_BLOCK.findall(text)
    if not candidates:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("no JSON object found in the reply")
        candidates = [text[start : end + 1]]
    try:
        data = json.loads(candidates[-1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"the JSON is not valid ({exc.msg} at position {exc.pos})") from None
    if not isinstance(data, dict):
        raise ValueError("the JSON must be an object")
    return data
