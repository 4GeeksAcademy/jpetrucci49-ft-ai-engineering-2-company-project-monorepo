"""Decision labels for a pending memory proposal. Not a substring `yes` test."""

from __future__ import annotations

import re
from typing import Literal

DecisionLabel = Literal["approve", "reject", "edit", "unclear"]

_EDIT = re.compile(
    r"(?:remember this instead|change (?:it|that) to|actually remember)\s*[:\-]\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)
_APPROVE = re.compile(
    r"^\s*(?:yes|yeah|yep|yup|sure|ok|okay|please do|go ahead|"
    r"do it|confirmed|affirmative|remember it|remember that)"
    r"(?:\s+please)?\s*[.!]?\s*$",
    re.IGNORECASE,
)
_REJECT = re.compile(
    r"^\s*(?:no|nope|nah|don't|do not|never(?: mind)?|forget it|"
    r"don't remember|do not remember|reject)"
    r"(?:\s+please)?\s*[.!]?\s*$",
    re.IGNORECASE,
)


def classify_memory_decision(message: str, pending: dict | None) -> tuple[DecisionLabel, str | None]:
    """High-confidence labeled patterns only. Anything else is unclear."""
    del pending
    text = (message or "").strip()
    if not text:
        return "unclear", None
    edit = _EDIT.search(text)
    if edit:
        replacement = edit.group(1).strip()
        if replacement:
            return "edit", replacement
        return "unclear", None
    if _APPROVE.search(text):
        return "approve", None
    if _REJECT.search(text):
        return "reject", None
    return "unclear", None
