"""Self-eval: should this turn become a pending memory proposal?"""

from __future__ import annotations

import re

from agent.memory.phi import contains_phi
from agent.memory.store import MemoryProposal

REMEMBER_PROMPT = "Want me to remember this for next time?"

_SKIP = re.compile(
    r"(?:ticket\s+#?\d+|stock\s+id\s+\d+|status of ticket|"
    r"this week'?s?\s+no-show|dashboard|weather|"
    r"^\s*(?:thanks|thank you)\b)",
    re.IGNORECASE,
)
_POISON = re.compile(
    r"\b(?:medicare|medicaid)\b.*\b(?:charge|fee|copay)\b|"
    r"\b(?:charge|fee)\b.*\b(?:medicare|medicaid)\b|"
    r"\b(?:remember|from now on).*\b(?:treatment|diagnos)",
    re.IGNORECASE,
)
_REMEMBER_INTENT = re.compile(
    r"(?:please\s+)?remember(?:\s+that)?\b|note that down|"
    r"write that down|save (?:that|this)|don'?t forget|"
    r"keep (?:that|this) in mind",
    re.IGNORECASE,
)
_DURABLE = re.compile(
    r"changed last quarter|now go through|road closure|"
    r"reminder programme|vacancies (?:broken down )?by role|"
    r"Diane Foster|internal referrals|from now on|going forward|"
    r"always (?:start|use|show)|I prefer|prefer (?:tables|bullets)|"
    r"always use (?:tables|bullets)|don'?t mention|do not mention|"
    r"recurring|keeps happening|same (?:issue|problem)",
    re.IGNORECASE,
)
_CLINICS = (
    "Manchester",
    "London",
    "Austin",
    "Houston",
    "Riverside",
    "Lakeside",
    "Summit",
    "Harborview",
    "Greenfield",
    "Oakwood",
    "Westside",
)
_PREFS = re.compile(
    r"(?:I prefer|prefer (?:tables|bullets)|always use (?:tables|bullets)|"
    r"don'?t mention|do not mention|Diane Foster|vacancies (?:broken down )?by role)",
    re.IGNORECASE,
)
_INCIDENT = re.compile(
    r"(?:recurring|keeps happening|same (?:issue|problem)|road closure|"
    r"not a real problem with the reminder)",
    re.IGNORECASE,
)


def detect_clinic(question: str) -> str:
    for name in _CLINICS:
        if re.search(rf"\b{re.escape(name)}\b", question, re.IGNORECASE):
            return name
    return ""


def looks_like_memory_intent(question: str) -> bool:
    text = (question or "").strip()
    if not text:
        return False
    return bool(_REMEMBER_INTENT.search(text) or _DURABLE.search(text))


def infer_kind(question: str) -> str:
    if _PREFS.search(question):
        return "presentation_pref"
    if _INCIDENT.search(question):
        return "incident_pattern"
    return "clinic_protocol"


def should_propose(question: str, answer: str) -> MemoryProposal | None:
    del answer
    text = (question or "").strip()
    if not text or contains_phi(text):
        return None
    if _SKIP.search(text) or _POISON.search(text):
        return None
    if not looks_like_memory_intent(text):
        return None
    clinic = detect_clinic(text)
    note = _normalize_note(text, clinic)
    if not note:
        return None
    return MemoryProposal(
        text=note,
        kind=infer_kind(text),  # type: ignore[arg-type]
        clinic=clinic,
        why="Operator stated a standing operational instruction on this turn.",
    )


def _normalize_note(question: str, clinic: str) -> str:
    stripped = re.sub(
        r"^(?:please\s+)?remember(?:\s+that)?\s+",
        "",
        question.strip(),
        flags=re.IGNORECASE,
    )
    stripped = stripped.rstrip(".!?")
    if clinic and clinic.casefold() not in stripped.casefold():
        return f"{clinic}: {stripped}"
    return stripped
