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

_QUASI_CLINIC = re.compile(
    r"\b(?:Austin|Manchester|London|Houston|Dallas|Miami|Orlando|Tampa|"
    r"Atlanta|Savannah|clinic)\b",
    re.IGNORECASE,
)
_QUASI_AGE = re.compile(r"\b(?:age\s*)?\d{1,3}\b")
_QUASI_DX = re.compile(r"\bdiagnos", re.IGNORECASE)
_QUASI_NAME = re.compile(
    r"\b(?:patient|named|john|i have a patient)\b",
    re.IGNORECASE,
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


def redact_phi(text: str) -> tuple[str, bool]:
    """Replace identifier spans with ``[REDACTED]``. Uses the same patterns as ``contains_phi``."""
    blob = text or ""
    if not contains_phi(blob):
        return blob, False
    redacted = blob
    for pattern in _PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted, True


def contains_quasi_identifier(text: str) -> bool:
    """Age + diagnosis + clinic, or name/patient + age + clinic."""
    blob = (text or "").strip()
    if not blob:
        return False
    age = bool(_QUASI_AGE.search(blob))
    clinic = bool(_QUASI_CLINIC.search(blob))
    dx = bool(_QUASI_DX.search(blob))
    name = bool(_QUASI_NAME.search(blob))
    return (age and dx and clinic) or (name and age and clinic)


def contains_phi_or_quasi(text: str) -> bool:
    return contains_phi(text) or contains_quasi_identifier(text)
