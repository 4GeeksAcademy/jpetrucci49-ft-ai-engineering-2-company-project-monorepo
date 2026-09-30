"""Ticket and section writes for approval. Part 1 and Part 2 JSON stay read-only."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from agent.memory.phi import contains_phi
from data.pipelines.rfp_approval.arbitrate import PHI_STUB
from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS
from rfp.models import RfpDepartmentSection, RfpMetadata, RfpTicket, utc_now

logger = logging.getLogger(__name__)

APPROVAL_PIPELINE_ERROR = "approval_pipeline_error"


def _open_session() -> Session:
    from inventory.database import get_session_factory

    return get_session_factory()()


def _dept_from_handoff(handoff: dict[str, Any], department_id: str) -> dict[str, Any]:
    for row in (handoff or {}).get("departments") or []:
        if isinstance(row, dict) and row.get("department_id") == department_id:
            return row
    return {}


def load_context(ticket_id: str) -> dict[str, Any]:
    """Part 2 drafts plus read-only Part 1 metadata and aspects."""
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")
        if not ticket.part2_handoff_json:
            raise ValueError(f"ticket {ticket_id} has no part2_handoff_json")
        handoff = dict(ticket.handoff_json or {})
        metadata = dict(handoff.get("metadata") or {})
        meta_row = session.exec(select(RfpMetadata).where(RfpMetadata.ticket_id == ticket_id)).first()
        if meta_row is not None:
            metadata.setdefault("client_name", meta_row.client_name)
            metadata.setdefault("client_country", meta_row.client_country)
            metadata.setdefault("covered_population", meta_row.covered_population)
            metadata.setdefault("currency", meta_row.currency)
        sections = session.exec(
            select(RfpDepartmentSection).where(RfpDepartmentSection.ticket_id == ticket_id)
        ).all()
        by_row = {row.department_id: row for row in sections}
        departments: dict[str, dict[str, Any]] = {}
        for dept, owner in DEPARTMENT_OWNERS.items():
            part2 = _dept_from_handoff(ticket.part2_handoff_json, dept)
            part1 = _dept_from_handoff(handoff, dept)
            row = by_row.get(dept)
            draft = str(part2.get("draft_content") or (row.draft_content if row else "") or "")
            evaluation = dict(part2.get("evaluation_results") or (row.evaluation_results if row else {}) or {})
            if contains_phi(draft):
                draft = PHI_STUB
                compliance = dict(evaluation.get("compliance") or {})
                compliance["contains_phi"] = True
                compliance["pass"] = False
                evaluation["compliance"] = compliance
            departments[dept] = {
                "department_id": dept,
                "owner": str(part2.get("owner") or owner),
                "draft_content": draft,
                "evaluation_results": evaluation,
                "needs_human_review": bool(part2.get("needs_human_review")),
                "key_aspects": [str(item) for item in (part1.get("key_aspects") or (row.key_aspects if row else []) or [])],
                "open_questions": [str(item) for item in (part1.get("open_questions") or (row.open_questions if row else []) or [])],
            }
        return {"ticket_id": ticket_id, "metadata": metadata, "handoff": handoff, "departments": departments}
    finally:
        session.close()


def set_status(ticket_id: str, status: str, *, error_code: str | None = None) -> None:
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")
        ticket.status = status
        ticket.error_code = error_code
        ticket.updated_at = utc_now()
        session.add(ticket)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def persist_approval_error(ticket_id: str) -> None:
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            return
        if ticket.status not in {"waiting_for_approval", "under_evaluation", "needs_human_review"}:
            ticket.status = "waiting_for_approval"
        ticket.error_code = APPROVAL_PIPELINE_ERROR
        ticket.updated_at = utc_now()
        session.add(ticket)
        session.commit()
    except Exception:
        logger.exception("failed to mark approval_pipeline_error")
        session.rollback()
    finally:
        session.close()


def save_section(
    ticket_id: str,
    department_id: str,
    *,
    draft_content: str,
    evaluation_results: dict[str, Any],
    approval_status: str | None,
    approver: str | None,
    approved_at: datetime | None,
) -> None:
    session = _open_session()
    try:
        row = session.exec(
            select(RfpDepartmentSection).where(
                RfpDepartmentSection.ticket_id == ticket_id,
                RfpDepartmentSection.department_id == department_id,
            )
        ).first()
        if row is None:
            row = RfpDepartmentSection(
                ticket_id=ticket_id,
                department_id=department_id,
                key_aspects=[],
                open_questions=[],
            )
        row.draft_content = draft_content
        row.evaluation_results = evaluation_results
        row.approval_status = approval_status
        row.approver = approver
        row.approved_at = approved_at
        session.add(row)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def load_sections(ticket_id: str) -> list[dict[str, Any]]:
    session = _open_session()
    try:
        rows = session.exec(
            select(RfpDepartmentSection).where(RfpDepartmentSection.ticket_id == ticket_id)
        ).all()
        return [
            {
                "department_id": row.department_id,
                "draft_content": row.draft_content or "",
                "evaluation_results": dict(row.evaluation_results or {}),
                "approval_status": row.approval_status,
                "approver": row.approver,
                "approved_at": row.approved_at,
            }
            for row in rows
        ]
    finally:
        session.close()


def save_final(ticket_id: str, document: dict[str, Any]) -> None:
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")
        ticket.final_document_json = document
        ticket.status = "done"
        ticket.error_code = None
        ticket.updated_at = utc_now()
        session.add(ticket)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def currency_for(metadata: dict[str, Any]) -> str:
    country = metadata.get("client_country")
    if country == "UK":
        return "GBP"
    if country == "US":
        return "USD"
    return str(metadata.get("currency") or "")
