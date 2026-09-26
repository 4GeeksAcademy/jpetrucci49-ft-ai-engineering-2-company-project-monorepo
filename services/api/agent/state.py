"""Minimal desk-turn state. One question → one answer. No conversation history."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict


class DeskAgentState(TypedDict):
    run_id: str
    question: str
    context: list[dict]
    answer: str
    error: str
    intent: str
    incident_query: dict
    incident_result: dict
    path: Annotated[list[str], add]
