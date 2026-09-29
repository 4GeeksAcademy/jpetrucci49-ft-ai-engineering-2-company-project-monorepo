"""Canned short-circuit answers. No PHI in the copy."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from agent.harness.classify import InputLabel, classify_input
from agent.harness.observe import record

COMPLIANCE_REDIRECT = (
    "For HealthCore work, ask a HIPAA, UK GDPR, breach-notification, "
    "BAA/DPA, or clinic-policy question and I can look it up."
)

INJECTION_REFUSE = (
    "I can't change my instructions or drop HealthCore compliance rules. "
    + COMPLIANCE_REDIRECT
)
PERSONAL_REFUSE = (
    "I can't help with personal tasks like that. I'm HealthCore's compliance "
    "assistant for HIPAA, UK GDPR, and internal clinic procedures. "
    + COMPLIANCE_REDIRECT
)
PHI_INPUT_REFUSE = (
    "I can't discuss a specific patient case, even hypothetically, when it "
    "includes identifiable or quasi-identifiable details. Please rephrase "
    "without names, ages, record numbers, or clinic-plus-diagnosis combinations."
)
SENSITIVE_REFUSE = (
    "I can't discuss details of active or under-investigation security breaches, "
    "or vendor-specific BAA/DPA commercial terms. You can ask about HealthCore's "
    "published breach-notification windows (60 days under HIPAA, 72 hours to the ICO) "
    "in general policy terms."
)

_SHORT_CIRCUIT: dict[InputLabel, str] = {
    "injection": INJECTION_REFUSE,
    "personal": PERSONAL_REFUSE,
    "phi": PHI_INPUT_REFUSE,
    "sensitive": SENSITIVE_REFUSE,
}


def canned_casual(question: str) -> str:
    tokyo = ""
    if "tokyo" in (question or "").casefold() and "time" in (question or "").casefold():
        try:
            stamp = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%H:%M")
            tokyo = f"It's about {stamp} in Tokyo. "
        except Exception:
            tokyo = "I don't keep a live world clock here. "
    elif "weather" in (question or "").casefold():
        tokyo = "I don't have a live weather feed. "
    return f"{tokyo}{COMPLIANCE_REDIRECT}".strip()


def apply_input_guard(question: str, *, run_id: str) -> tuple[InputLabel, str | None]:
    """Return (label, canned_answer_or_none). None means fall through to the graph."""
    label = classify_input(question)
    if label == "domain":
        return label, None
    if label == "casual":
        record("casual", run_id=run_id)
        return label, canned_casual(question)
    record(label, run_id=run_id)
    return label, _SHORT_CIRCUIT[label]
