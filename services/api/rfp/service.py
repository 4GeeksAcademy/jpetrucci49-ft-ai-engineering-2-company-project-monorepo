"""Create tickets and schedule the intake graph. Routers do not own agent logic."""

from __future__ import annotations

import logging
from uuid import uuid4

from sqlmodel import Session, select

from data.pipelines.paths import RAW_DIR
from data.pipelines.rfp_intake.persist import persist_pipeline_error
from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS
from rfp.models import RfpDepartmentSection, RfpMetadata, RfpTicket, utc_now
from rfp.schemas import (
    DepartmentSectionOut,
    RfpMetadataOut,
    TicketCreated,
    TicketOut,
    TicketSectionsOut,
)

logger = logging.getLogger(__name__)

RFP_RAW_DIR = RAW_DIR / "rfp"


class RfpTicketNotFoundError(LookupError):
    pass


def create_ticket(session: Session, *, pdf_bytes: bytes, created_by: str) -> TicketCreated:
    ticket_id = str(uuid4())
    RFP_RAW_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = RFP_RAW_DIR / f"{ticket_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)
    ticket = RfpTicket(
        ticket_id=ticket_id,
        status="analyzing",
        raw_pdf_path=str(pdf_path),
        created_by=created_by,
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return TicketCreated(ticket_id=ticket.ticket_id, status=ticket.status)


def run_intake_job(ticket_id: str) -> None:
    from data.pipelines.rfp_intake.graph import run_rfp_intake

    try:
        run_rfp_intake(ticket_id)
    except Exception:
        logger.exception("rfp intake failed")
        persist_pipeline_error(ticket_id)


def get_ticket(session: Session, ticket_id: str) -> TicketOut:
    ticket = session.get(RfpTicket, ticket_id)
    if ticket is None:
        raise RfpTicketNotFoundError(ticket_id)
    meta = session.exec(select(RfpMetadata).where(RfpMetadata.ticket_id == ticket_id)).first()
    metadata_out = None
    if meta is not None:
        metadata_out = RfpMetadataOut(
            client_name=meta.client_name,
            client_country=meta.client_country,
            program_type=meta.program_type,
            covered_population=meta.covered_population,
            deadline=meta.deadline,
            budget_range=meta.budget_range,
            currency=meta.currency,
            departments_needed=list(meta.departments_needed or []),
            readability=dict(meta.readability or {}),
        )
    return TicketOut(
        ticket_id=ticket.ticket_id,
        rfp_id=ticket.rfp_id,
        status=ticket.status,
        discard_reason=ticket.discard_reason,
        error_code=ticket.error_code,
        phi_detected=ticket.phi_detected,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        metadata=metadata_out,
        handoff_json=ticket.handoff_json if ticket.status == "intake_complete" else None,
    )


def get_sections(session: Session, ticket_id: str) -> TicketSectionsOut:
    ticket = session.get(RfpTicket, ticket_id)
    if ticket is None:
        raise RfpTicketNotFoundError(ticket_id)
    rows = session.exec(
        select(RfpDepartmentSection).where(RfpDepartmentSection.ticket_id == ticket_id)
    ).all()
    by_dept = {row.department_id: row for row in rows}
    sections = [
        DepartmentSectionOut(
            department_id=dept,
            owner=owner,
            key_aspects=list((by_dept[dept].key_aspects if dept in by_dept else None) or []),
            open_questions=list((by_dept[dept].open_questions if dept in by_dept else None) or []),
        )
        for dept, owner in DEPARTMENT_OWNERS.items()
    ]
    return TicketSectionsOut(ticket_id=ticket_id, sections=sections)


def touch_updated_at(session: Session, ticket_id: str) -> None:
    ticket = session.get(RfpTicket, ticket_id)
    if ticket is None:
        return
    ticket.updated_at = utc_now()
    session.add(ticket)
