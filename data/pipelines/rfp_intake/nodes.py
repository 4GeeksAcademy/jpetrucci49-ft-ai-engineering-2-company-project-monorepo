"""Graph nodes: convert → classify → orchestrate → workers → synthesize → persist."""

from __future__ import annotations

from typing import Any, Literal

from data.pipelines.rfp_intake.classify import classify_rfp
from data.pipelines.rfp_intake.convert import convert_document
from data.pipelines.rfp_intake.extracts import department_extracts
from data.pipelines.rfp_intake.persist import persist_complete, persist_conversion, persist_discarded
from data.pipelines.rfp_intake.state import RfpIntakeState
from data.pipelines.rfp_intake.workers import run_worker, synthesize


def convert_node(state: RfpIntakeState) -> dict[str, Any]:
    result = convert_document(
        ticket_id=state["ticket_id"],
        pdf_path=state.get("pdf_path") or "",
        markdown=state.get("markdown") or None,
    )
    persist_conversion(
        state["ticket_id"],
        markdown_path=result["markdown_path"],
        phi_detected=result["phi_detected"],
        metadata=result["metadata"],
    )
    return {
        "markdown": result["markdown"],
        "markdown_path": result["markdown_path"],
        "phi_detected": result["phi_detected"],
        "metadata": result["metadata"],
    }


def classify_node(state: RfpIntakeState) -> dict[str, Any]:
    verdict = classify_rfp(state.get("markdown") or "")
    metadata = dict(state.get("metadata") or {})
    if verdict.get("program_type") and verdict["program_type"] != "unknown":
        metadata["program_type"] = verdict["program_type"]
    return {
        "is_rfp": bool(verdict["is_rfp"]),
        "discard_reason": None if verdict["is_rfp"] else "not_an_rfp",
        "metadata": metadata,
    }


def route_after_classify(state: RfpIntakeState) -> Literal["persist_discarded", "orchestrate"]:
    if state.get("is_rfp"):
        return "orchestrate"
    return "persist_discarded"


def persist_discarded_node(state: RfpIntakeState) -> dict[str, Any]:
    persist_discarded(state["ticket_id"], state.get("discard_reason") or "not_an_rfp")
    return {}


def orchestrate_node(state: RfpIntakeState) -> dict[str, Any]:
    return {"extracts": department_extracts(state.get("markdown") or "")}


def _worker_update(department_id: str, state: RfpIntakeState) -> dict[str, Any]:
    extracts = state.get("extracts") or {}
    result = run_worker(
        department_id,
        state.get("metadata") or {},
        extracts.get(department_id) or "",
        phi_detected=bool(state.get("phi_detected")),
    )
    return {"worker_results": {department_id: result}}


def revenue_worker_node(state: RfpIntakeState) -> dict[str, Any]:
    return _worker_update("revenue", state)


def clinical_worker_node(state: RfpIntakeState) -> dict[str, Any]:
    return _worker_update("clinical", state)


def compliance_worker_node(state: RfpIntakeState) -> dict[str, Any]:
    return _worker_update("compliance", state)


def synthesize_node(state: RfpIntakeState) -> dict[str, Any]:
    handoff = synthesize(
        state["ticket_id"],
        state.get("metadata") or {},
        state.get("worker_results") or {},
        phi_detected=bool(state.get("phi_detected")),
    )
    return {"synthesizer": handoff}


def persist_complete_node(state: RfpIntakeState) -> dict[str, Any]:
    persist_complete(
        state["ticket_id"],
        metadata=state.get("metadata") or {},
        worker_results=state.get("worker_results") or {},
        handoff=state.get("synthesizer") or {},
        phi_detected=bool(state.get("phi_detected")),
    )
    return {}
