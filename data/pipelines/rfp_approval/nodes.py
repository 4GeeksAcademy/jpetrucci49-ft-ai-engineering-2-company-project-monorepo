"""Department branch nodes. Interrupt lives only in ``wait_node``."""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from data.pipelines.rfp_approval.arbitrate import PHI_STUB, triggers_for
from data.pipelines.rfp_approval.decisions import MAX_APPROVAL_ITERATIONS
from data.pipelines.rfp_approval.persist import save_section
from data.pipelines.rfp_approval.state import BranchState
from data.pipelines.rfp_approval.trace import event
from data.pipelines.rfp_draft.generate import generate_section
from rfp.models import utc_now as ticket_now


def _drafts(state: BranchState) -> dict[str, str]:
    drafts = dict(state.get("drafts") or {})
    drafts[state["department_id"]] = state.get("draft_content") or ""
    return drafts


def approval_payload(state: BranchState) -> dict[str, Any]:
    metadata = state.get("metadata") or {}
    return {
        "ticket_id": state.get("ticket_id"),
        "department_id": state.get("department_id"),
        "owner": state.get("owner"),
        "client_name": metadata.get("client_name") or "",
        "client_country": metadata.get("client_country") or "unknown",
        "currency": metadata.get("currency") or "",
        "covered_population": metadata.get("covered_population"),
        "draft_content": state.get("draft_content") or "",
        "evaluation_results": state.get("evaluation_results") or {},
        "needs_human_review": bool(state.get("needs_human_review")),
        "open_questions": list(state.get("open_questions") or []),
        "blocking_triggers": list(state.get("blocking_triggers") or []),
    }


def _persist_branch(state: BranchState, *, approval_status: str | None, approver: str | None, approved_at: Any) -> None:
    evaluation = dict(state.get("evaluation_results") or {})
    if state.get("arbitration"):
        evaluation = {**evaluation, "arbitration": list(state.get("arbitration") or [])}
    save_section(
        state["ticket_id"],
        state["department_id"],
        draft_content=state.get("draft_content") or "",
        evaluation_results=evaluation,
        approval_status=approval_status,
        approver=approver,
        approved_at=approved_at,
    )


def guard_node(state: BranchState) -> dict[str, Any]:
    draft = state.get("draft_content") or ""
    evaluation = dict(state.get("evaluation_results") or {})
    from agent.memory.phi import contains_phi

    if contains_phi(draft):
        draft = PHI_STUB
        compliance = dict(evaluation.get("compliance") or {})
        compliance["contains_phi"] = True
        compliance["pass"] = False
        evaluation["compliance"] = compliance
    triggers = triggers_for(
        state["department_id"],
        drafts=_drafts({**state, "draft_content": draft}),
        aspects=state.get("aspects") or {},
        evaluations={state["department_id"]: evaluation},
        metadata=state.get("metadata") or {},
    )
    ids = [item["trigger_id"] for item in triggers]
    return {
        "draft_content": draft,
        "evaluation_results": evaluation,
        "arbitration": triggers,
        "blocking_triggers": ids,
        "trace": [event("guard", state["department_id"], "section", ",".join(ids) or "clear")],
    }


def arbitrate_node(state: BranchState) -> dict[str, Any]:
    ids = list(state.get("blocking_triggers") or [])
    return {
        "trace": [event("arbitrate", state["department_id"], "triggers", ",".join(ids) or "none")],
    }


def mark_wait_node(state: BranchState) -> dict[str, Any]:
    _persist_branch(state, approval_status=state.get("approval_status"), approver=None, approved_at=None)
    return {
        "trace": [event("interrupt_approval", state["department_id"], "waiting_for_approval", "interrupted")],
    }


def wait_node(state: BranchState) -> dict[str, Any]:
    decision = interrupt(approval_payload(state))
    if not isinstance(decision, dict):
        decision = {}
    return {"pending_decision": decision}


def route_after_guard(state: BranchState) -> str:
    if state.get("blocking_triggers"):
        return "arbitrate"
    return "mark_wait"


def apply_node(state: BranchState) -> dict[str, Any]:
    decision = dict(state.get("pending_decision") or {})
    kind = decision.get("decision") or ""
    triggers = list(state.get("blocking_triggers") or [])
    dept = state["department_id"]
    if kind == "approve" and triggers:
        return {
            "approval_status": None,
            "route": "mark_wait",
            "trace": [event("resume_approval", dept, "approve", f"approve_refused:{triggers[0]}")],
        }
    if kind == "approve":
        approved_at = ticket_now()
        _persist_branch(state, approval_status="approved", approver=state.get("owner"), approved_at=approved_at)
        return {
            "approval_status": "approved",
            "route": "done",
            "trace": [event("resume_approval", dept, "approve", "approved")],
        }
    if kind == "reject":
        _persist_branch(state, approval_status="rejected", approver=None, approved_at=None)
        return {
            "approval_status": "rejected",
            "route": "mark_wait",
            "trace": [event("resume_approval", dept, "reject", "rejected")],
        }
    nxt = int(state.get("iteration") or 0) + 1
    if nxt >= MAX_APPROVAL_ITERATIONS:
        _persist_branch(state, approval_status="changes_requested", approver=None, approved_at=None)
        return {
            "iteration": nxt,
            "approval_status": "changes_requested",
            "route": "mark_wait",
            "trace": [event("resume_approval", dept, "request_changes", "approval_iteration_cap")],
        }
    return {
        "iteration": nxt,
        "approval_status": "changes_requested",
        "route": "revise",
        "trace": [event("resume_approval", dept, "request_changes", "revise")],
    }


def route_after_apply(state: BranchState) -> str:
    return state.get("route") or "mark_wait"


def revise_node(state: BranchState) -> dict[str, Any]:
    comment = str((state.get("pending_decision") or {}).get("comment") or "")
    draft = generate_section(state["department_id"], state.get("handoff") or {}, feedback=comment)
    drafts = dict(state.get("drafts") or {})
    drafts[state["department_id"]] = draft
    return {
        "draft_content": draft,
        "drafts": drafts,
        "approval_status": "changes_requested",
        "trace": [event("revise", state["department_id"], "request_changes", "draft_updated")],
    }

