"""Minimal desk-turn state. One question → one answer. No conversation history."""

from __future__ import annotations

from typing import TypedDict


class DeskAgentState(TypedDict):
    run_id: str
    question: str
    context: list[dict]
    answer: str
    error: str
