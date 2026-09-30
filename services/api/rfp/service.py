"""Create tickets and schedule the intake graph. Routers do not own agent logic."""

from __future__ import annotations

import logging
from uuid import uuid4

from sqlmodel import Session, select

from data.pipelines.paths import RAW_DIR
from data.pipelines.rfp_intake.persist import persist_pipeline_error
from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS
from rfp.models import RfpDepartmentSection, RfpMetadata, RfpTicket, utc_now
from rfp.events import publish_ticket_created
from rfp.schemas import (
    DepartmentSectionOut,
    RfpMetadataOut,
    TicketCreated,
    TicketNotice,
    TicketNoticeList,
    TicketOut,
    TicketSectionsOut,
)

logger = logging.getLogger(__name__)

RFP_RAW_DIR = RAW_DIR / "rfp"


class RfpTicketNotFoundError(LookupError):
    pass


class RfpTicketConflictError(ValueError):
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
    publish_ticket_created(ticket.ticket_id, ticket.status)
    return TicketCreated(ticket_id=ticket.ticket_id, status=ticket.status)


def list_recent_tickets(session: Session, *, limit: int = 20) -> TicketNoticeList:
    """Newest committed tickets. This table is the record when nobody was listening."""
    statement = select(RfpTicket).order_by(RfpTicket.created_at.desc()).limit(limit)
    rows = session.exec(statement).all()
    return TicketNoticeList(
        tickets=[TicketNotice(ticket_id=row.ticket_id, status=row.status) for row in rows]
    )


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
        handoff_json=ticket.handoff_json,
        part2_handoff_json=ticket.part2_handoff_json,
        final_document_json=ticket.final_document_json,
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
            draft_content=by_dept[dept].draft_content if dept in by_dept else None,
            evaluation_results=by_dept[dept].evaluation_results if dept in by_dept else None,
            approval_status=by_dept[dept].approval_status if dept in by_dept else None,
            approver=by_dept[dept].approver if dept in by_dept else None,
            approved_at=by_dept[dept].approved_at if dept in by_dept else None,
            blocking_triggers=_blocking_triggers(ticket_id, dept),
        )
        for dept, owner in DEPARTMENT_OWNERS.items()
    ]
    return TicketSectionsOut(ticket_id=ticket_id, sections=sections)


def _blocking_triggers(ticket_id: str, department_id: str) -> list[str]:
    try:
        from data.pipelines.rfp_approval.graph import branch_interrupt

        payload = branch_interrupt(ticket_id, department_id)
    except Exception:
        return []
    if not payload:
        return []
    return [str(item) for item in (payload.get("blocking_triggers") or [])]


_APPROVAL_ENTRY = frozenset({"under_evaluation", "needs_human_review"})


def start_approvals(session: Session, ticket_id: str) -> TicketCreated:
    """Open department interrupts before the 202 response is sent."""
    ticket = session.get(RfpTicket, ticket_id)
    if ticket is None:
        raise RfpTicketNotFoundError(ticket_id)
    if not ticket.part2_handoff_json:
        raise RfpTicketConflictError("Ticket has no proposal draft to approve.")
    from data.pipelines.rfp_approval.decisions import ApprovalNotWaiting
    from data.pipelines.rfp_approval.graph import any_branch_waiting
    from data.pipelines.rfp_approval.graph import start_approvals as run_approvals

    waiting = any_branch_waiting(ticket_id)
    retry = ticket.status == "waiting_for_approval" and not waiting
    if ticket.status not in _APPROVAL_ENTRY and not retry:
        raise RfpTicketConflictError("Ticket is not ready for department approval.")
    if waiting:
        raise RfpTicketConflictError("Department approval is already waiting.")
    try:
        run_approvals(ticket_id)
    except ApprovalNotWaiting as exc:
        raise RfpTicketConflictError(str(exc)) from exc
    return TicketCreated(ticket_id=ticket_id, status="waiting_for_approval")


def submit_approval(
    session: Session,
    ticket_id: str,
    department_id: str,
    *,
    decision: str,
    comment: str | None,
    approver: str,
    draft_content: str | None = None,
) -> TicketOut:
    ticket = session.get(RfpTicket, ticket_id)
    if ticket is None:
        raise RfpTicketNotFoundError(ticket_id)
    from data.pipelines.rfp_approval.graph import resume_approval

    # Approve stores draft_content when the manager edited the proposal on the card.
    resume_approval(
        ticket_id,
        department_id,
        decision,
        comment,
        approver=approver,
        draft_content=draft_content,
    )
    session.expire_all()
    return get_ticket(session, ticket_id)


def start_draft(session: Session, ticket_id: str) -> TicketCreated:
    ticket = session.get(RfpTicket, ticket_id)
    if ticket is None:
        raise RfpTicketNotFoundError(ticket_id)
    if ticket.status in {"discarded", "analyzing"} or not ticket.handoff_json:
        raise RfpTicketConflictError("Ticket is not ready for draft generation.")
    retryable = (
        ticket.status in {"drafting", "under_evaluation"}
        and ticket.error_code == "draft_pipeline_error"
    )
    if ticket.status != "intake_complete" and not retryable:
        raise RfpTicketConflictError("Draft generation is already running or finished.")
    ticket.status = "drafting"
    ticket.error_code = None
    ticket.updated_at = utc_now()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return TicketCreated(ticket_id=ticket.ticket_id, status=ticket.status)


def run_draft_job(ticket_id: str) -> None:
    from data.pipelines.rfp_draft.graph import run_rfp_draft
    from data.pipelines.rfp_draft.persist import persist_draft_pipeline_error

    try:
        run_rfp_draft(ticket_id)
    except Exception:
        logger.exception("rfp draft failed")
        persist_draft_pipeline_error(ticket_id)


def touch_updated_at(session: Session, ticket_id: str) -> None:
    ticket = session.get(RfpTicket, ticket_id)
    if ticket is None:
        return
    ticket.updated_at = utc_now()
    session.add(ticket)
