"""Named nodes for ``rfp_draft``. Evaluators write disjoint ``eval_parts`` keys only."""

from __future__ import annotations

from typing import Any

from data.pipelines.rfp_draft.evaluate import (
    MAX_DRAFT_ITERATIONS,
    combine_evaluation,
    evaluate_compliance,
    evaluate_readability,
    evaluate_relevance,
)
from data.pipelines.rfp_draft.generate import DEPARTMENTS, generate_section
from data.pipelines.rfp_draft.persist import load_handoff, persist_drafts, persist_status
from data.pipelines.rfp_draft.state import RfpDraftState


def _dept_row(handoff: dict[str, Any], department_id: str) -> dict[str, Any]:
    for row in (handoff or {}).get("departments") or []:
        if isinstance(row, dict) and row.get("department_id") == department_id:
            return row
    return {"key_aspects": [], "open_questions": []}


def assign_node(state: RfpDraftState) -> dict[str, Any]:
    ticket_id = state["ticket_id"]
    handoff = load_handoff(ticket_id)
    persist_status(ticket_id, "drafting")
    known = {
        row.get("department_id")
        for row in (handoff.get("departments") or [])
        if isinstance(row, dict)
    }
    pending = [dept for dept in DEPARTMENTS if not known or dept in known]
    return {
        "handoff": handoff,
        "iteration": {dept: 0 for dept in DEPARTMENTS},
        "drafts": {},
        "eval_parts": {},
        "results": {},
        "feedback": {},
        "pending": pending or list(DEPARTMENTS),
        "error_code": None,
    }


def _generate_node(department_id: str):
    def node(state: RfpDraftState) -> dict[str, Any]:
        pending = state.get("pending") or []
        if department_id not in pending:
            return {}
        draft = generate_section(
            department_id,
            state.get("handoff") or {},
            feedback=(state.get("feedback") or {}).get(department_id),
        )
        current = (state.get("iteration") or {}).get(department_id, 0)
        return {
            "drafts": {department_id: draft},
            "iteration": {department_id: current + 1},
        }

    node.__name__ = f"generate_{department_id}_node"
    return node


generate_revenue_node = _generate_node("revenue")
generate_clinical_node = _generate_node("clinical")
generate_compliance_node = _generate_node("compliance")


def mark_under_evaluation_node(state: RfpDraftState) -> dict[str, Any]:
    persist_status(state["ticket_id"], "under_evaluation")
    return {}


def eval_readability_node(state: RfpDraftState) -> dict[str, Any]:
    pending = state.get("pending") or list(DEPARTMENTS)
    drafts = state.get("drafts") or {}
    return {
        "eval_parts": {
            dept: {"readability": evaluate_readability(drafts.get(dept, ""))} for dept in pending
        }
    }


def eval_relevance_node(state: RfpDraftState) -> dict[str, Any]:
    pending = state.get("pending") or list(DEPARTMENTS)
    drafts = state.get("drafts") or {}
    handoff = state.get("handoff") or {}
    parts: dict[str, dict[str, Any]] = {}
    for dept in pending:
        aspects = [str(item) for item in _dept_row(handoff, dept).get("key_aspects") or []]
        parts[dept] = {"relevance": evaluate_relevance(drafts.get(dept, ""), aspects)}
    return {"eval_parts": parts}


def eval_compliance_node(state: RfpDraftState) -> dict[str, Any]:
    pending = state.get("pending") or list(DEPARTMENTS)
    drafts = state.get("drafts") or {}
    handoff = state.get("handoff") or {}
    metadata = dict(handoff.get("metadata") or {})
    parts: dict[str, dict[str, Any]] = {}
    for dept in pending:
        aspects = [str(item) for item in _dept_row(handoff, dept).get("key_aspects") or []]
        parts[dept] = {
            "compliance": evaluate_compliance(
                drafts.get(dept, ""),
                department_id=dept,
                metadata=metadata,
                key_aspects=aspects,
            )
        }
    return {"eval_parts": parts}


def combine_eval_node(state: RfpDraftState) -> dict[str, Any]:
    pending = state.get("pending") or list(DEPARTMENTS)
    parts = state.get("eval_parts") or {}
    iteration = state.get("iteration") or {}
    results = dict(state.get("results") or {})
    feedback = dict(state.get("feedback") or {})
    next_pending: list[str] = []
    for dept in pending:
        count = int(iteration.get(dept, 1))
        capped = count >= MAX_DRAFT_ITERATIONS
        result = combine_evaluation(dept, parts.get(dept) or {}, iteration=count, capped=capped)
        results[dept] = result
        feedback[dept] = str(result.get("feedback_for_generator") or "")
        if not result["overall_pass"] and not capped:
            next_pending.append(dept)
    return {
        "results": results,
        "feedback": feedback,
        "pending": next_pending,
    }


def dispatch_revise_node(state: RfpDraftState) -> dict[str, Any]:
    return {}


def persist_node(state: RfpDraftState) -> dict[str, Any]:
    persist_drafts(
        state["ticket_id"],
        drafts=state.get("drafts") or {},
        results=state.get("results") or {},
    )
    return {}


def route_after_combine(state: RfpDraftState) -> str:
    if state.get("pending"):
        return "dispatch_revise"
    return "persist"
