"""Read-only incident lookup. Calls the existing manager — no fake store."""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Literal

from pydantic import BaseModel, Field

from app.incidents.models import (
    IncidentBranch,
    IncidentCategory,
    IncidentOrigin,
    IncidentPublic,
    IncidentStatus,
)

logger = logging.getLogger(__name__)

INCIDENT_LOOKUP_TIMEOUT_SECONDS = 5
TICKET_FALLBACK = "I couldn't confirm that ticket's status right now"
LIST_CAP = 5

IncidentError = Literal["not_found", "timeout", "unavailable"]

_ID = re.compile(
    r"(?:(?:ticket|incident)\s*#?\s*(\d+)|(?<![\w/])#(\d+))",
    re.IGNORECASE,
)
_INCIDENT_WORDS = re.compile(
    r"\b(?:ticket|incident|tickets|incidents)\b",
    re.IGNORECASE,
)
_POLICY_WORDS = re.compile(
    r"\b(?:cancel|cancellation|cancelling|no-show|noshow|no show|"
    r"insurance|insurer|medicaid|medicare|referral|specialist|"
    r"new[- ]patient|documents?|checklist|coverage|fee|charge|"
    r"late-cancel|late cancel)\b",
    re.IGNORECASE,
)

BRANCH_LABELS: dict[str, str] = {
    "central": "Central — Austin Main Clinic",
    "austin_north": "Austin — North",
    "dallas_uptown": "Dallas Uptown",
    "houston_med_center": "Houston Medical Center",
    "san_antonio_west": "San Antonio West",
    "miami_brickell": "Miami Brickell",
    "miami_doral": "Miami Doral",
    "orlando_east": "Orlando East",
    "tampa_bay": "Tampa Bay",
    "atlanta_midtown": "Atlanta Midtown",
    "savannah": "Savannah",
    "london_city": "London City",
    "london_west": "London West End",
    "manchester_central": "Manchester Central",
}
CATEGORY_LABELS: dict[str, str] = {
    "clinical_equipment": "Clinical equipment",
    "it_system": "IT system",
    "billing_error": "Billing error",
    "compliance_breach": "Compliance breach",
    "patient_experience": "Patient experience",
    "staff_issue": "Staff issue",
    "facility_issue": "Facility issue",
    "referral_issue": "Referral issue",
    "other": "Other",
}
STATUS_LABELS: dict[str, str] = {
    "open": "Open",
    "in_progress": "In progress",
    "resolved": "Resolved",
    "discarded": "Discarded",
}
ORIGIN_LABELS: dict[str, str] = {
    "customer": "Customer",
    "branch": "Branch",
    "internal": "Internal",
}


class IncidentLookupIn(BaseModel):
    incident_id: int | None = None
    status: IncidentStatus | None = None
    category: IncidentCategory | None = None
    origin: IncidentOrigin | None = None
    branch: IncidentBranch | None = None


class IncidentRecord(BaseModel):
    id: int
    title: str
    description: str
    category: IncidentCategory
    status: IncidentStatus
    origin: IncidentOrigin
    branch: IncidentBranch
    created_at: str
    updated_at: str


class IncidentLookupOut(BaseModel):
    ok: bool
    incidents: list[IncidentRecord] = Field(default_factory=list)
    error: IncidentError | None = None


def lookup_timeout_seconds() -> int:
    raw = os.environ.get("INCIDENT_LOOKUP_TIMEOUT_SECONDS", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return INCIDENT_LOOKUP_TIMEOUT_SECONDS


def parse_incident_lookup(question: str) -> IncidentLookupIn:
    text = question.strip()
    match = _ID.search(text)
    incident_id = None
    if match:
        raw_id = match.group(1) or match.group(2)
        incident_id = int(raw_id)
    status = _parse_status(text) if incident_id is None else None
    return IncidentLookupIn(incident_id=incident_id, status=status)


def classify_question(question: str) -> tuple[str, IncidentLookupIn]:
    lookup = parse_incident_lookup(question)
    asks_incident = lookup.incident_id is not None or bool(_INCIDENT_WORDS.search(question))
    asks_policy = bool(_POLICY_WORDS.search(question))
    if asks_incident and asks_policy:
        return "both", lookup
    if asks_incident:
        return "incident", lookup
    return "rag", lookup


def get_incident(incident_id: int) -> IncidentPublic | None:
    from app.incidents.manager import get_incident as _get_incident

    return _get_incident(incident_id)


def list_incidents(
    *,
    status: IncidentStatus | None = None,
    origin: IncidentOrigin | None = None,
    branch: IncidentBranch | None = None,
    category: IncidentCategory | None = None,
) -> list[IncidentPublic]:
    from app.incidents.manager import list_incidents as _list_incidents

    return _list_incidents(
        status=status,
        origin=origin,
        branch=branch,
        category=category,
    )


def lookup_incidents(query: IncidentLookupIn) -> IncidentLookupOut:
    timeout = lookup_timeout_seconds()
    try:
        if query.incident_id is not None:
            incident = _call(lambda: get_incident(query.incident_id), timeout)
            if incident is None:
                return IncidentLookupOut(ok=False, incidents=[], error="not_found")
            return IncidentLookupOut(ok=True, incidents=[_to_record(incident)], error=None)
        if not any((query.status, query.category, query.origin, query.branch)):
            return IncidentLookupOut(ok=False, incidents=[], error="not_found")
        rows = _call(
            lambda: list_incidents(
                status=query.status,
                origin=query.origin,
                branch=query.branch,
                category=query.category,
            ),
            timeout,
        )
        records = [_to_record(row) for row in (rows or [])[:LIST_CAP]]
        if not records:
            return IncidentLookupOut(ok=False, incidents=[], error="not_found")
        return IncidentLookupOut(ok=True, incidents=records, error=None)
    except TimeoutError:
        return IncidentLookupOut(ok=False, incidents=[], error="timeout")
    except Exception:
        logger.exception("incident lookup unavailable")
        return IncidentLookupOut(ok=False, incidents=[], error="unavailable")


def ticket_sentence(result: IncidentLookupOut | dict) -> str:
    payload = (
        result
        if isinstance(result, IncidentLookupOut)
        else IncidentLookupOut.model_validate(result or {})
    )
    if not payload.ok or not payload.incidents:
        return TICKET_FALLBACK
    return format_incident_answer(payload)


def format_incident_answer(result: IncidentLookupOut) -> str:
    lines = [_format_one(row) for row in result.incidents]
    return "\n\n".join(lines)


def _format_one(row: IncidentRecord) -> str:
    status = STATUS_LABELS.get(row.status, row.status)
    category = CATEGORY_LABELS.get(row.category, row.category)
    origin = ORIGIN_LABELS.get(row.origin, row.origin)
    clinic = BRANCH_LABELS.get(row.branch, row.branch)
    return (
        f"Ticket {row.id} is {status}. "
        f"Title: {row.title}. "
        f"Category: {category}. "
        f"Origin: {origin}. "
        f"Clinic: {clinic}. "
        f"Opened: {row.created_at}. "
        f"Updated: {row.updated_at}."
    )


def _to_record(incident: IncidentPublic) -> IncidentRecord:
    payload = incident.model_dump(mode="json")
    return IncidentRecord.model_validate(payload)


def _parse_status(text: str) -> IncidentStatus | None:
    lowered = text.lower()
    if "in progress" in lowered or "in_progress" in lowered:
        return IncidentStatus.IN_PROGRESS
    if re.search(r"\bresolved\b", lowered):
        return IncidentStatus.RESOLVED
    if re.search(r"\bdiscarded\b", lowered):
        return IncidentStatus.DISCARDED
    if re.search(r"\bopen\b", lowered):
        return IncidentStatus.OPEN
    return None


def _call(fn, timeout: float):
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout as exc:
            raise TimeoutError("incident lookup timed out") from exc
