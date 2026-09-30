"""Per-department interrupt threads plus a parent join. No parent interrupt."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from data.pipelines.paths import RAW_DIR
from data.pipelines.rfp_approval.decisions import ApprovalBlocked, ApprovalNotWaiting, parse_decision
from data.pipelines.rfp_approval.nodes import (
    apply_node,
    arbitrate_node,
    guard_node,
    mark_wait_node,
    revise_node,
    route_after_apply,
    route_after_guard,
    wait_node,
)
from data.pipelines.rfp_approval.persist import (
    currency_for,
    load_context,
    load_sections,
    persist_approval_error,
    save_final,
    set_status,
)
from data.pipelines.rfp_approval.state import BranchState, JoinState
from data.pipelines.rfp_approval.trace import write_trace
from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS
from rfp.models import utc_now

_saver: SqliteSaver | None = None
_conn: sqlite3.Connection | None = None
_branch = None
_join = None


def checkpoint_path() -> Path:
    override = os.getenv("RFP_APPROVAL_CHECKPOINT_PATH", "").strip()
    return Path(override) if override else RAW_DIR / "rfp_approval.sqlite"


def reset_checkpointer(path: str | None = None) -> None:
    """Point the saver at a new sqlite file. Tests call this with a temp path."""
    global _saver, _conn, _branch, _join
    if _conn is not None:
        _conn.close()
    _saver = None
    _conn = None
    _branch = None
    _join = None
    if path:
        os.environ["RFP_APPROVAL_CHECKPOINT_PATH"] = path


def get_checkpointer() -> SqliteSaver:
    global _saver, _conn
    if _saver is None:
        path = checkpoint_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(path), check_same_thread=False)
        _saver = SqliteSaver(_conn)
        _saver.setup()
    return _saver


def _branch_graph():
    global _branch
    if _branch is None:
        builder = StateGraph(BranchState)
        builder.add_node("guard", guard_node)
        builder.add_node("arbitrate", arbitrate_node)
        builder.add_node("mark_wait", mark_wait_node)
        builder.add_node("wait", wait_node)
        builder.add_node("apply", apply_node)
        builder.add_node("revise", revise_node)
        builder.add_edge(START, "guard")
        builder.add_conditional_edges("guard", route_after_guard, {"arbitrate": "arbitrate", "mark_wait": "mark_wait"})
        builder.add_edge("arbitrate", "mark_wait")
        builder.add_edge("mark_wait", "wait")
        builder.add_edge("wait", "apply")
        builder.add_conditional_edges(
            "apply",
            route_after_apply,
            {"done": END, "revise": "revise", "mark_wait": "mark_wait"},
        )
        builder.add_edge("revise", "guard")
        _branch = builder.compile(checkpointer=get_checkpointer())
    return _branch


def _join_node(state: JoinState) -> dict[str, Any]:
    ticket_id = state["ticket_id"]
    rows = {row["department_id"]: row for row in load_sections(ticket_id)}
    context = load_context(ticket_id)
    approved = [
        dept
        for dept in DEPARTMENT_OWNERS
        if rows.get(dept, {}).get("approval_status") == "approved"
    ]
    phi = any(
        bool(((rows.get(dept) or {}).get("evaluation_results") or {}).get("compliance", {}).get("contains_phi"))
        for dept in DEPARTMENT_OWNERS
    )
    if len(approved) == 3 and not phi:
        document = {
            "ticket_id": ticket_id,
            "sections": [
                {
                    "department_id": dept,
                    "owner": DEPARTMENT_OWNERS[dept],
                    "approver": rows[dept].get("approver"),
                    "approved_at": rows[dept]["approved_at"].isoformat()
                    if rows[dept].get("approved_at")
                    else utc_now().isoformat(),
                    "draft_content": rows[dept].get("draft_content") or "",
                }
                for dept in DEPARTMENT_OWNERS
            ],
            "currency": currency_for(context["metadata"]),
            "generated_at": utc_now().isoformat(),
        }
        save_final(ticket_id, document)
    else:
        set_status(ticket_id, "waiting_for_approval", error_code=None)
    _flush_trace(ticket_id)
    return {}


def _join_graph():
    global _join
    if _join is None:
        builder = StateGraph(JoinState)
        builder.add_node("join", _join_node)
        builder.add_edge(START, "join")
        builder.add_edge("join", END)
        _join = builder.compile(checkpointer=get_checkpointer())
    return _join


def thread_id(ticket_id: str, department_id: str | None = None) -> str:
    if department_id:
        return f"rfp-{ticket_id}:{department_id}"
    return f"rfp-{ticket_id}"


def _config(ticket_id: str, department_id: str | None = None) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id(ticket_id, department_id)}}


def branch_interrupt(ticket_id: str, department_id: str) -> dict[str, Any] | None:
    snap = _branch_graph().get_state(_config(ticket_id, department_id))
    pending = list(getattr(snap, "interrupts", ()) or ())
    for task in getattr(snap, "tasks", ()) or ():
        pending.extend(getattr(task, "interrupts", ()) or ())
    for item in pending:
        value = getattr(item, "value", None)
        if isinstance(value, dict):
            return value
    return None


def branch_waiting(ticket_id: str, department_id: str) -> bool:
    return branch_interrupt(ticket_id, department_id) is not None


def any_branch_waiting(ticket_id: str) -> bool:
    return any(branch_waiting(ticket_id, dept) for dept in DEPARTMENT_OWNERS)


def _initial(ticket_id: str, department_id: str, context: dict[str, Any]) -> BranchState:
    departments = context["departments"]
    current = departments[department_id]
    metadata = dict(context["metadata"])
    metadata["currency"] = currency_for(metadata)
    return {
        "ticket_id": ticket_id,
        "department_id": department_id,
        "owner": current["owner"],
        "metadata": metadata,
        "key_aspects": current["key_aspects"],
        "open_questions": current["open_questions"],
        "draft_content": current["draft_content"],
        "evaluation_results": current["evaluation_results"],
        "needs_human_review": current["needs_human_review"],
        "handoff": context["handoff"],
        "drafts": {dept: departments[dept]["draft_content"] for dept in departments},
        "aspects": {dept: departments[dept]["key_aspects"] for dept in departments},
        "iteration": 0,
        "blocking_triggers": [],
        "arbitration": [],
        "pending_decision": {},
        "approval_status": None,
        "route": "",
        "trace": [],
    }


def _invoke_branch(ticket_id: str, department_id: str, payload: BranchState | Command) -> None:
    _branch_graph().invoke(payload, _config(ticket_id, department_id))


def _flush_trace(ticket_id: str) -> None:
    events: list[dict[str, Any]] = []
    graph = _branch_graph()
    for dept in DEPARTMENT_OWNERS:
        snap = graph.get_state(_config(ticket_id, dept))
        values = snap.values or {}
        events.extend(values.get("trace") or [])
    write_trace(ticket_id, events)


def _run_join(ticket_id: str) -> None:
    _join_graph().invoke({"ticket_id": ticket_id}, _config(ticket_id))


def start_approvals(ticket_id: str) -> None:
    """Open three department threads and leave each one interrupted."""
    try:
        if any_branch_waiting(ticket_id):
            raise ApprovalNotWaiting("Approval threads are already waiting.")
        context = load_context(ticket_id)
        set_status(ticket_id, "waiting_for_approval", error_code=None)
        for dept in DEPARTMENT_OWNERS:
            _invoke_branch(ticket_id, dept, _initial(ticket_id, dept, context))
        _run_join(ticket_id)
    except ApprovalNotWaiting:
        raise
    except Exception:
        persist_approval_error(ticket_id)
        raise


def resume_approval(ticket_id: str, department_id: str, decision: str, comment: str | None) -> None:
    """Resume one department thread, then join. Other threads stay put."""
    if department_id not in DEPARTMENT_OWNERS:
        raise InvalidDepartment(department_id)
    payload = branch_interrupt(ticket_id, department_id)
    if payload is None:
        raise ApprovalNotWaiting(department_id)
    parsed = parse_decision(decision, comment)
    blocking = list(payload.get("blocking_triggers") or [])
    if parsed["decision"] == "approve" and blocking:
        raise ApprovalBlocked(str(blocking[0]))
    try:
        _invoke_branch(ticket_id, department_id, Command(resume=parsed))
        _run_join(ticket_id)
    except Exception:
        persist_approval_error(ticket_id)
        raise


class InvalidDepartment(ValueError):
    pass
