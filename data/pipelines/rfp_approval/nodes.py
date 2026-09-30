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


def _persist_branch(
    state: BranchState,
    *,
    approval_status: str | None,
    approver: str | None,
    approved_at: Any,
    draft_content: str | None = None,
    evaluation_results: dict[str, Any] | None = None,
) -> None:
    evaluation = dict(evaluation_results if evaluation_results is not None else (state.get("evaluation_results") or {}))
    if state.get("arbitration"):
        evaluation = {**evaluation, "arbitration": list(state.get("arbitration") or [])}
    save_section(
        state["ticket_id"],
        state["department_id"],
        draft_content=state.get("draft_content") if draft_content is None else draft_content,
        evaluation_results=evaluation,
        approval_status=approval_status,
        approver=approver,
        approved_at=approved_at,
    )


def _with_decision(state: BranchState, kind: str, comment: str, *, capped: bool) -> dict[str, Any]:
    evaluation = dict(state.get("evaluation_results") or {})
    evaluation["last_decision"] = {"decision": kind, "comment": comment, "capped": capped}
    return evaluation


def _edited_draft(state: BranchState) -> str:
    return str((state.get("pending_decision") or {}).get("draft_content") or "").strip()


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
        approver = str(decision.get("approver") or "").strip() or state.get("owner")
        draft = _edited_draft(state) or (state.get("draft_content") or "")
        evaluation = dict(state.get("evaluation_results") or {})
        from agent.memory.phi import contains_phi

        if contains_phi(draft):
            draft = PHI_STUB
            compliance = dict(evaluation.get("compliance") or {})
            compliance["contains_phi"] = True
            compliance["pass"] = False
            evaluation["compliance"] = compliance
        _persist_branch(
            state,
            approval_status="approved",
            approver=approver,
            approved_at=approved_at,
            draft_content=draft,
            evaluation_results=evaluation,
        )
        return {
            "draft_content": draft,
            "evaluation_results": evaluation,
            "approval_status": "approved",
            "route": "done",
            "trace": [event("resume_approval", dept, "approve", "approved")],
        }
    comment = str(decision.get("comment") or "")
    edited = _edited_draft(state)
    if kind == "reject":
        evaluation = _with_decision(state, "reject", comment, capped=False)
        draft = edited or (state.get("draft_content") or "")
        _persist_branch(
            state,
            approval_status="rejected",
            approver=None,
            approved_at=None,
            draft_content=draft,
            evaluation_results=evaluation,
        )
        return {
            "draft_content": draft,
            "evaluation_results": evaluation,
            "approval_status": "rejected",
            "route": "mark_wait",
            "trace": [event("resume_approval", dept, "reject", "rejected")],
        }
    nxt = int(state.get("iteration") or 0) + 1
    if nxt >= MAX_APPROVAL_ITERATIONS:
        evaluation = _with_decision(state, "request_changes", comment, capped=True)
        draft = edited or (state.get("draft_content") or "")
        _persist_branch(
            state,
            approval_status="changes_requested",
            approver=None,
            approved_at=None,
            draft_content=draft,
            evaluation_results=evaluation,
        )
        return {
            "iteration": nxt,
            "draft_content": draft,
            "evaluation_results": evaluation,
            "approval_status": "changes_requested",
            "route": "mark_wait",
            "trace": [event("resume_approval", dept, "request_changes", "approval_iteration_cap")],
        }
    return {
        "iteration": nxt,
        "evaluation_results": _with_decision(state, "request_changes", comment, capped=False),
        "approval_status": "changes_requested",
        "route": "revise",
        "trace": [event("resume_approval", dept, "request_changes", "revise")],
    }


def route_after_apply(state: BranchState) -> str:
    return state.get("route") or "mark_wait"


def revise_node(state: BranchState) -> dict[str, Any]:
    edited = _edited_draft(state)
    if edited:
        draft = edited
        summary = "draft_edited"
    else:
        comment = str((state.get("pending_decision") or {}).get("comment") or "")
        draft = generate_section(state["department_id"], state.get("handoff") or {}, feedback=comment)
        summary = "draft_updated"
    drafts = dict(state.get("drafts") or {})
    drafts[state["department_id"]] = draft
    return {
        "draft_content": draft,
        "drafts": drafts,
        "approval_status": "changes_requested",
        "trace": [event("revise", state["department_id"], "request_changes", summary)],
    }

