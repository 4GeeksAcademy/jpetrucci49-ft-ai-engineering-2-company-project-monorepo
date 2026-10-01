"""SQLModel writes for RFP intake. Re-scan PHI before every commit."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from agent.memory.phi import contains_phi
from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS
from rfp.events import format_created_at, publish_rfp_ticket_created
from rfp.models import RfpDepartmentSection, RfpMetadata, RfpTicket, utc_now

logger = logging.getLogger(__name__)

PHI_BLOCKED = "Content blocked pending Compliance review."


def _open_session() -> Session:
    from inventory.database import get_session_factory

    return get_session_factory()()


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return PHI_BLOCKED if contains_phi(value) else value
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub(item) for key, item in value.items()}
    return value


def _text_blobs(*values: Any) -> list[str]:
    blobs: list[str] = []
    for value in values:
        if isinstance(value, str):
            blobs.append(value)
        else:
            blobs.append(json.dumps(value, default=str))
    return blobs


def _refuse_if_phi(*values: Any) -> None:
    for blob in _text_blobs(*values):
        if contains_phi(blob):
            raise ValueError("phi_in_persist")


def persist_conversion(
    ticket_id: str,
    *,
    markdown_path: str,
    phi_detected: bool,
    metadata: dict[str, Any],
) -> None:
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")
        ticket.markdown_path = markdown_path
        ticket.phi_detected = bool(phi_detected)
        ticket.updated_at = utc_now()
        _upsert_metadata(session, ticket, metadata)
        session.add(ticket)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def persist_discarded(ticket_id: str, reason: str) -> None:
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")
        ticket.status = "discarded"
        ticket.discard_reason = reason if reason in {"not_an_rfp", "pipeline_error"} else "pipeline_error"
        if ticket.discard_reason == "pipeline_error":
            ticket.error_code = "pipeline_error"
        ticket.updated_at = utc_now()
        session.add(ticket)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def persist_pipeline_error(ticket_id: str) -> None:
    try:
        persist_discarded(ticket_id, "pipeline_error")
    except Exception:
        logger.exception("failed to mark pipeline_error for ticket")


def persist_complete(
    ticket_id: str,
    *,
    metadata: dict[str, Any],
    worker_results: dict[str, Any],
    handoff: dict[str, Any],
    phi_detected: bool,
) -> None:
    session = _open_session()
    notice: dict[str, str | None] | None = None
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")

        safe_handoff = _scrub(handoff)
        try:
            _refuse_if_phi(safe_handoff, metadata, worker_results)
        except ValueError:
            safe_handoff = _scrub(handoff)
            logger.warning("rfp persist scrubbed residual PHI markers ticket_id=%s", ticket_id)

        metadata_row = _upsert_metadata(session, ticket, metadata)
        _upsert_sections(session, ticket_id, worker_results, phi_detected=phi_detected)
        # Freeze the notice while the ticket is still analyzing. Send it only after
        # commit so a rolled-back write does not reach the dashboard.
        notice = {
            "ticket_id": ticket.ticket_id,
            "rfp_id": ticket.rfp_id,
            "client_name": metadata_row.client_name if isinstance(metadata_row.client_name, str) else None,
            "client_country": metadata_row.client_country,
            "program_type": metadata_row.program_type,
            "status": ticket.status,
            "created_at": format_created_at(ticket.created_at),
        }

        ticket.status = "intake_complete"
        ticket.discard_reason = None
        ticket.error_code = None
        ticket.phi_detected = bool(phi_detected)
        ticket.handoff_json = safe_handoff
        ticket.updated_at = utc_now()
        session.add(ticket)
        session.commit()
    except Exception:
        session.rollback()
        notice = None
        raise
    finally:
        session.close()
    if notice is not None:
        publish_rfp_ticket_created(notice)


def load_ticket_pdf_path(ticket_id: str) -> str:
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")
        return ticket.raw_pdf_path
    finally:
        session.close()


def _upsert_metadata(session: Session, ticket: RfpTicket, metadata: dict[str, Any]) -> RfpMetadata:
    row = session.exec(select(RfpMetadata).where(RfpMetadata.ticket_id == ticket.ticket_id)).first()
    payload = {
        "client_name": _scrub(metadata.get("client_name")),
        "client_country": metadata.get("client_country") or "unknown",
        "program_type": metadata.get("program_type") or "unknown",
        "covered_population": metadata.get("covered_population"),
        "deadline": _scrub(metadata.get("deadline")),
        "budget_range": _scrub(metadata.get("budget_range")),
        "currency": metadata.get("currency"),
        "departments_needed": list(metadata.get("departments_needed") or ["revenue", "clinical", "compliance"]),
        "readability": dict(metadata.get("readability") or {}),
    }
    if row is None:
        row = RfpMetadata(id=str(uuid4()), ticket_id=ticket.ticket_id, **payload)
        session.add(row)
        session.flush()
        ticket.rfp_id = row.id
    else:
        for key, value in payload.items():
            setattr(row, key, value)
        session.add(row)
        ticket.rfp_id = row.id
    return row


def _upsert_sections(
    session: Session,
    ticket_id: str,
    worker_results: dict[str, Any],
    *,
    phi_detected: bool,
) -> None:
    for dept in DEPARTMENT_OWNERS:
        raw = worker_results.get(dept) if isinstance(worker_results, dict) else None
        aspects = _scrub(list((raw or {}).get("key_aspects") or []))
        questions = _scrub(list((raw or {}).get("open_questions") or []))
        evaluation = {"contains_phi": True} if dept == "compliance" and phi_detected else None

        existing = session.exec(
            select(RfpDepartmentSection).where(
                RfpDepartmentSection.ticket_id == ticket_id,
                RfpDepartmentSection.department_id == dept,
            )
        ).first()
        if existing is None:
            session.add(
                RfpDepartmentSection(
                    ticket_id=ticket_id,
                    department_id=dept,
                    key_aspects=aspects,
                    open_questions=questions,
                    evaluation_results=evaluation,
                )
            )
        else:
            existing.key_aspects = aspects
            existing.open_questions = questions
            if evaluation is not None:
                existing.evaluation_results = evaluation
            session.add(existing)
