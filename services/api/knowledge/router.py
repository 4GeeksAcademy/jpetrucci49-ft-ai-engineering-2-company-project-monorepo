"""POST /knowledge/query — generated answer only. Retrieval lives in data/pipelines."""

from __future__ import annotations

from typing import Annotated

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.dependencies import get_current_user
from auth.models import UserPublic
from data.pipelines.rag import query as answer_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeQueryIn(BaseModel):
    question: str = Field(..., min_length=1)


class KnowledgeQueryOut(BaseModel):
    answer: str


@router.post("/query", response_model=KnowledgeQueryOut)
def knowledge_query(
    body: KnowledgeQueryIn,
    _: Annotated[UserPublic, Depends(get_current_user)],
) -> KnowledgeQueryOut:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")
    try:
        answer = answer_question(question)
    except RuntimeError as exc:
        logger.warning("knowledge query unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("knowledge query failed")
        raise HTTPException(
            status_code=500, detail="Unable to answer from the knowledge base."
        ) from exc
    return KnowledgeQueryOut(answer=answer)
