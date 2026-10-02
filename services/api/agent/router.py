"""HTTP for the compiled desk graph. No retrieve/generate logic here."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from pydantic import BaseModel

from agent.chat import serve_chat
from agent.graph import run_desk_agent
from agent.harness.observe import summary as guardrail_summary
from agent.nodes import EMPTY_QUESTION
from agent.rate_limit import RATE_LIMIT_DETAIL, allow_agent_query
from agent.traces import load_trace
from auth.dependencies import get_current_user
from auth.models import UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.websocket("/chat")
async def agent_chat(websocket: WebSocket) -> None:
    await serve_chat(websocket)


class AgentQueryIn(BaseModel):
    question: str = ""


class AgentQueryOut(BaseModel):
    answer: str
    run_id: str


@router.post("/query", response_model=AgentQueryOut)
def agent_query(
    body: AgentQueryIn,
    user: Annotated[UserPublic, Depends(get_current_user)],
) -> AgentQueryOut:
    if not allow_agent_query(user.id):
        raise HTTPException(status_code=429, detail=RATE_LIMIT_DETAIL)
    try:
        result = run_desk_agent(body.question, user_id=user.id)
    except RuntimeError as exc:
        logger.warning("agent query unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("agent query failed")
        raise HTTPException(
            status_code=500, detail="Unable to answer from the knowledge base."
        ) from exc
    error = result.get("error") or ""
    if error == EMPTY_QUESTION:
        raise HTTPException(status_code=400, detail=EMPTY_QUESTION)
    if error:
        raise HTTPException(status_code=503, detail=error)
    return AgentQueryOut(answer=result.get("answer") or "", run_id=result["run_id"])


@router.get("/traces/{run_id}")
def agent_trace(
    run_id: str,
    _: Annotated[UserPublic, Depends(get_current_user)],
) -> dict[str, Any]:
    payload = load_trace(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return payload


@router.get("/guardrails/summary")
def agent_guardrail_summary(
    _: Annotated[UserPublic, Depends(get_current_user)],
) -> dict[str, Any]:
    return {"counts": guardrail_summary()}
