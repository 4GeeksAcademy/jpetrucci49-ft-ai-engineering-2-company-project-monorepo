"""HIPAA + UK GDPR identifier scan. One function, both regimes."""

from __future__ import annotations

import re

_PATTERNS = (
    re.compile(r"\bpatients?\s+[A-Za-z][A-Za-z'-]+\b", re.IGNORECASE),
    re.compile(r"\b(?:mrn|medical record(?:\s+number)?)\b[:#]?\s*\w+", re.IGNORECASE),
    re.compile(r"\bnhs\s+number\b[:#]?\s*\w*", re.IGNORECASE),
    re.compile(r"\bnhs\s*[:#]\s*\d+", re.IGNORECASE),
    re.compile(r"\b(?:dob|date of birth)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:diagnos(?:is|ed)|lab results?|clinical notes?|visit notes?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\binsurance\s+(?:number|id|#)\b", re.IGNORECASE),
    re.compile(r"\b(?:ssn|national insurance)\b", re.IGNORECASE),
)

PHI_REFUSAL = (
    "I can't remember that. HealthCore memory cannot store patient identifiers "
    "or PHI under HIPAA or UK GDPR."
)


def contains_phi(text: str) -> bool:
    blob = (text or "").strip()
    if not blob:
        return False
    return any(pattern.search(blob) for pattern in _PATTERNS)
