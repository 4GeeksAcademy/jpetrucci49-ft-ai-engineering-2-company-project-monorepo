"""JWT RFP intake routes. Trigger and query only — graph lives in ``data/pipelines``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from auth.dependencies import get_current_user
from auth.models import UserPublic
from inventory.database import get_db
from rfp import service as rfp_service
from rfp.schemas import TicketCreated, TicketOut, TicketSectionsOut

router = APIRouter(prefix="/rfp", tags=["rfp"])

CurrentUser = Annotated[UserPublic, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


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
