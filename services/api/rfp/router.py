"""JWT RFP intake routes. Trigger and query only — graph lives in ``data/pipelines``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session

from auth.dependencies import get_current_user
from auth.models import UserPublic, UserRole
from auth.services.profiles import get_profile_by_user_id
from inventory.database import get_db
from rfp import service as rfp_service
from rfp.events import event_stream, subscribe
from rfp.schemas import (
    ApprovalDecisionIn,
    TicketCreated,
    TicketNoticeList,
    TicketOut,
    TicketSectionsOut,
)

router = APIRouter(prefix="/rfp", tags=["rfp"])

CurrentUser = Annotated[UserPublic, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
_DECISION_ROLES = {UserRole.manager, UserRole.admin}


def _signed_in_approver(user: UserPublic) -> str:
    profile = get_profile_by_user_id(user.id)
    if profile is not None and profile.name.strip():
        return profile.name.strip()
    return str(user.email)


def _is_pdf(filename: str, content: bytes) -> bool:
    name = (filename or "").lower()
    if not name.endswith(".pdf"):
        return False
    return content.startswith(b"%PDF") or len(content) > 0


@router.post("/tickets", status_code=status.HTTP_202_ACCEPTED)
async def upload_ticket(
    background_tasks: BackgroundTasks,
    session: DbSession,
    user: CurrentUser,
    file: UploadFile = File(..., description="Institutional RFP PDF"),
) -> JSONResponse:
    filename = file.filename or ""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if not _is_pdf(filename, content):
        raise HTTPException(status_code=400, detail="Upload a PDF file.")
    created: TicketCreated = rfp_service.create_ticket(
        session,
        pdf_bytes=content,
        created_by=str(user.id),
    )
    background_tasks.add_task(rfp_service.run_intake_job, created.ticket_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=created.model_dump(),
    )


@router.get("/tickets", response_model=TicketNoticeList)
def read_recent_tickets(session: DbSession, _: CurrentUser) -> TicketNoticeList:
    return rfp_service.list_recent_tickets(session)


@router.get("/events")
async def ticket_events(_: CurrentUser) -> StreamingResponse:
    subscriber = subscribe()
    return StreamingResponse(
        event_stream(subscriber),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tickets/{ticket_id}/draft", status_code=status.HTTP_202_ACCEPTED)
def start_draft(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    session: DbSession,
    _: CurrentUser,
) -> JSONResponse:
    try:
        created = rfp_service.start_draft(session, ticket_id)
    except rfp_service.RfpTicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Ticket not found.") from exc
    except rfp_service.RfpTicketConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(rfp_service.run_draft_job, ticket_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=created.model_dump(),
    )


@router.post("/tickets/{ticket_id}/approvals", status_code=status.HTTP_202_ACCEPTED)
def start_approvals(ticket_id: str, session: DbSession, _: CurrentUser) -> JSONResponse:
    try:
        created: TicketCreated = rfp_service.start_approvals(session, ticket_id)
    except rfp_service.RfpTicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Ticket not found.") from exc
    except rfp_service.RfpTicketConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=created.model_dump())


@router.post("/tickets/{ticket_id}/approvals/{department_id}", response_model=TicketOut)
def submit_approval(
    ticket_id: str,
    department_id: str,
    body: ApprovalDecisionIn,
    session: DbSession,
    user: CurrentUser,
) -> TicketOut:
    from data.pipelines.rfp_approval.decisions import ApprovalBlocked, ApprovalNotWaiting, InvalidDecision
    from data.pipelines.rfp_approval.graph import InvalidDepartment

    if user.role not in _DECISION_ROLES:
        raise HTTPException(status_code=403, detail="A manager has to record this department decision.")
    try:
        return rfp_service.submit_approval(
            session,
            ticket_id,
            department_id,
            decision=body.decision,
            comment=body.comment,
            approver=_signed_in_approver(user),
            draft_content=body.draft_content,
        )
    except rfp_service.RfpTicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Ticket not found.") from exc
    except InvalidDepartment as exc:
        raise HTTPException(status_code=400, detail="Unknown department.") from exc
    except InvalidDecision as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ApprovalBlocked as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Approve refused while {exc.trigger_id} is blocking.",
        ) from exc
    except ApprovalNotWaiting as exc:
        raise HTTPException(status_code=409, detail="That department is not waiting for a decision.") from exc


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def read_ticket(ticket_id: str, session: DbSession, _: CurrentUser) -> TicketOut:
    try:
        return rfp_service.get_ticket(session, ticket_id)
    except rfp_service.RfpTicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Ticket not found.") from exc


@router.get("/tickets/{ticket_id}/sections", response_model=TicketSectionsOut)
def read_sections(ticket_id: str, session: DbSession, _: CurrentUser) -> TicketSectionsOut:
    try:
        return rfp_service.get_sections(session, ticket_id)
    except rfp_service.RfpTicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Ticket not found.") from exc
