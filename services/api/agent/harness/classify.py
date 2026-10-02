"""Input labels for the desk-agent harness. Deterministic; no LLM."""

from __future__ import annotations

import re
from typing import Literal

from agent.memory.phi import contains_phi_or_quasi
from agent.tools.incidents import classify_question
from agent.tools.inventory import is_stock_ask

InputLabel = Literal["injection", "phi", "personal", "sensitive", "casual", "domain"]

_INJECTION = re.compile(
    r"(?:ignore(?:\s+\w+){0,4}\s+(?:instructions|rules|policies|prompt)|"
    r"reveal a patient identifier|"
    r"act as (?:an )?assistant with no|"
    r"you (?:are|have) now (?:an )?assistant with no rules|"
    r"you (?:are|have) no (?:compliance )?rules|"
    r"forget (?:that )?you work for|"
    r"no compliance rules|"
    r"jailbreak|"
    r"reveal (?:your )?(?:system )?prompt|"
    r"pretend you have no (?:rules|restrictions))",
    re.IGNORECASE,
)
_PERSONAL = re.compile(
    r"(?:personal email|salary raise|love poem|"
    r"university homework|help me with my homework|"
    r"write (?:me )?(?:an )?essay|"
    r"act(?:ing)? as a therapist|therapy session|"
    r"code for (?:my|another) project)",
    re.IGNORECASE,
)
_SENSITIVE = re.compile(
    r"(?:(?:active|under[- ]investigation|ongoing)\s+(?:security\s+)?breach|"
    r"(?:how many records|when was it discovered|which clinic)\b.{0,80}\b"
    r"(?:breach|cyber|security incident)|"
    r"\b(?:breach|cyber|security incident)\b.{0,80}\b"
    r"(?:how many records|when (?:was it )?discovered|which clinic)|"
    r"vendor[- ]specific (?:baa|dpa)|baa (?:commercial )?terms|"
    r"dpa (?:commercial )?terms)",
    re.IGNORECASE,
)
_CASUAL = re.compile(
    r"(?:\bweather\b|what time is it|time in \w+|how are you|"
    r"good (?:morning|afternoon|shift)|capital of |"
    r"tell me a joke|small talk)",
    re.IGNORECASE,
)
_DOMAIN_MARKERS = re.compile(
    r"\b(?:hipaa|gdpr|ico|baa|dpa|cancel|cancellation|no-show|"
    r"referral|medicare|medicaid|ticket|incident|stock|inventory|"
    r"policy|procedure|compliance|breach notification)\b",
    re.IGNORECASE,
)


def classify_input(question: str) -> InputLabel:
    text = (question or "").strip()
    if not text:
        return "domain"
    if _INJECTION.search(text):
        return "injection"
    if contains_phi_or_quasi(text):
        return "phi"
    if _PERSONAL.search(text):
        return "personal"
    if _SENSITIVE.search(text):
        return "sensitive"
    if _is_tool_or_policy(text):
        return "domain"
    if _CASUAL.search(text) and not _DOMAIN_MARKERS.search(text):
        return "casual"
    return "domain"


def _is_tool_or_policy(text: str) -> bool:
    intent, _ = classify_question(text)
    if intent in {"incident", "both"}:
        return True
    if is_stock_ask(text):
        return True
    return bool(_DOMAIN_MARKERS.search(text))
