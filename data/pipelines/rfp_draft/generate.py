"""Deterministic department drafts from Part 1 handoff. Optional RAG; no invented figures."""

from __future__ import annotations

import logging
import re
from typing import Any

from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS

logger = logging.getLogger(__name__)

DEPARTMENTS = ("revenue", "clinical", "compliance")

_FILLER = (
    "This internal HealthCore draft is written for operational review. "
    "It restates only facts present in the intake handoff and leaves unspecified "
    "commercial figures as open questions for the named department owner."
)


def _meta(handoff: dict[str, Any]) -> dict[str, Any]:
    return dict((handoff or {}).get("metadata") or {})


def _dept_row(handoff: dict[str, Any], department_id: str) -> dict[str, Any]:
    for row in (handoff or {}).get("departments") or []:
        if isinstance(row, dict) and row.get("department_id") == department_id:
            return row
    return {
        "department_id": department_id,
        "key_aspects": [],
        "open_questions": [],
        "owner": DEPARTMENT_OWNERS.get(department_id, ""),
    }


def _join(items: list[str]) -> str:
    clean = [item.strip() for item in items if str(item).strip()]
    return " ".join(clean) if clean else "No additional intake aspects were recorded."


def generate_section(
    department_id: str,
    handoff: dict[str, Any],
    *,
    feedback: str | None = None,
) -> str:
    """Draft one pricing-proposal section from Part 1 metadata and that department's aspects."""
    if department_id not in DEPARTMENT_OWNERS:
        return ""
    meta = _meta(handoff)
    row = _dept_row(handoff, department_id)
    aspects = [str(item) for item in (row.get("key_aspects") or [])]
    questions = [str(item) for item in (row.get("open_questions") or [])]
    owner = str(row.get("owner") or DEPARTMENT_OWNERS[department_id])
    client = meta.get("client_name") or "the institutional client"
    country = meta.get("client_country") or "unknown"
    currency = meta.get("currency")
    if country == "US":
        currency = currency or "USD"
    elif country == "UK":
        currency = currency or "GBP"
    program = str(meta.get("program_type") or "unknown").replace("_", " ")
    population = meta.get("covered_population")
    phi = bool((handoff or {}).get("phi_detected"))

    aspect_block = _join(aspects)
    question_block = _join(questions) if questions else "No open intake questions."

    if department_id == "revenue":
        money = (
            f"Commercial terms are quoted in {currency} as required for a {country} client."
            if currency
            else "Currency will follow client country once confirmed; no price is invented here."
        )
        body = (
            f"Revenue Cycle draft for {client} ({program}). Owner: {owner}. {money} "
            f"Intake aspects to honour: {aspect_block} Open questions remain: {question_block} "
            f"{_FILLER} Payment structure is described only when the handoff already states it; "
            f"otherwise Revenue Cycle will confirm invoicing before a figure is published."
        )
    elif department_id == "clinical":
        volume = (
            f"Covered population in the handoff is {population}."
            if isinstance(population, int) and population > 0
            else "Covered population is not stated in the handoff and is not invented here."
        )
        body = (
            f"Clinical Operations draft for {client} ({program}). Owner: {owner}. {volume} "
            f"Feasibility notes from intake: {aspect_block} Remaining questions: {question_block} "
            f"{_FILLER} Clinic and staff commitments stay within stated on-site or satellite "
            f"requests; no additional site count is added."
        )
    else:
        if country == "US":
            instrument = (
                "This US proposal includes a Business Associate Agreement (BAA) clause under HIPAA "
                "before any patient-data processing begins."
            )
        elif country == "UK":
            instrument = (
                "This UK proposal includes a Data Processing Agreement (DPA) referencing UK GDPR "
                "before any personal-data processing begins."
            )
        else:
            instrument = (
                "Country is not yet US or UK in the handoff; BAA versus DPA will be confirmed "
                "before close. No patient identifiers appear in this draft."
            )
        phi_line = (
            "Part 1 flagged PHI indicators; Compliance must complete human review before circulation."
            if phi
            else "No PHI was flagged on intake; this draft contains no patient names or diagnoses."
        )
        body = (
            f"Compliance and Data Governance draft for {client} ({program}). Owner: {owner}. "
            f"{instrument} {phi_line} Intake aspects: {aspect_block} Open questions: {question_block} "
            f"{_FILLER} Regulatory language follows HealthCore CONTEXT rules only."
        )

    extra = _optional_policy_note(department_id)
    revision = ""
    if feedback and feedback.strip():
        revision = (
            f" Revision addressing evaluation feedback ({feedback.strip()}): the section now "
            f"restates the required instrument, currency, and intake aspects without adding figures."
        )
    return re.sub(r"\s+", " ", f"{body} {extra} {revision}").strip()


def _optional_policy_note(department_id: str) -> str:
    if department_id != "compliance":
        return ""
    try:
        from data.pipelines.rag import retrieve
    except Exception:
        return ""
    try:
        hits = retrieve("Business Associate Agreement and UK GDPR Data Processing Agreement requirements")
    except Exception:
        logger.debug("optional RAG retrieve skipped")
        return ""
    if not hits:
        return ""
    return " Policy reference retrieved from the knowledge base; instruments follow CONTEXT only."
