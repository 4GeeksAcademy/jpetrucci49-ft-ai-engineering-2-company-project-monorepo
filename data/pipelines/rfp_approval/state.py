"""State for one department approval branch. No PHI spans."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


def append_trace(left: list[dict[str, Any]] | None, right: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [*(left or []), *(right or [])]


class BranchState(TypedDict, total=False):
    ticket_id: str
    department_id: str
    owner: str
    metadata: dict[str, Any]
    key_aspects: list[str]
    open_questions: list[str]
    draft_content: str
    evaluation_results: dict[str, Any]
    needs_human_review: bool
    handoff: dict[str, Any]
    drafts: dict[str, str]
    aspects: dict[str, list[str]]
    iteration: int
    blocking_triggers: list[str]
    arbitration: list[dict[str, Any]]
    pending_decision: dict[str, Any]
    approval_status: str | None
    route: str
    trace: Annotated[list[dict[str, Any]], append_trace]


class JoinState(TypedDict, total=False):
    ticket_id: str
