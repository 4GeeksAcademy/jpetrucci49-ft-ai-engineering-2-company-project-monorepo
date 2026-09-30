"""Compiled ``rfp_intake`` graph. Dedicated — do not mix into ``desk_graph``."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from data.pipelines.rfp_intake.nodes import (
    classify_node,
    clinical_worker_node,
    compliance_worker_node,
    convert_node,
    orchestrate_node,
    persist_complete_node,
    persist_discarded_node,
    revenue_worker_node,
    route_after_classify,
    synthesize_node,
)
from data.pipelines.rfp_intake.persist import load_ticket_pdf_path, persist_pipeline_error
from data.pipelines.rfp_intake.state import RfpIntakeState

GRAPH_NODES = frozenset(
    {
        "convert",
        "classify",
        "persist_discarded",
        "orchestrate",
        "revenue_worker",
        "clinical_worker",
        "compliance_worker",
        "synthesize",
        "persist_complete",
    }
)


def build_rfp_intake_graph() -> StateGraph:
    builder = StateGraph(RfpIntakeState)
    builder.add_node("convert", convert_node)
    builder.add_node("classify", classify_node)
    builder.add_node("persist_discarded", persist_discarded_node)
    builder.add_node("orchestrate", orchestrate_node)
    builder.add_node("revenue_worker", revenue_worker_node)
    builder.add_node("clinical_worker", clinical_worker_node)
    builder.add_node("compliance_worker", compliance_worker_node)
    builder.add_node("synthesize", synthesize_node)
    builder.add_node("persist_complete", persist_complete_node)

    builder.add_edge(START, "convert")
    builder.add_edge("convert", "classify")
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {"persist_discarded": "persist_discarded", "orchestrate": "orchestrate"},
    )
    builder.add_edge("persist_discarded", END)
    builder.add_edge("orchestrate", "revenue_worker")
    builder.add_edge("orchestrate", "clinical_worker")
    builder.add_edge("orchestrate", "compliance_worker")
    builder.add_edge("revenue_worker", "synthesize")
    builder.add_edge("clinical_worker", "synthesize")
    builder.add_edge("compliance_worker", "synthesize")
    builder.add_edge("synthesize", "persist_complete")
    builder.add_edge("persist_complete", END)
    return builder


rfp_intake_graph = build_rfp_intake_graph().compile()


def run_rfp_intake(ticket_id: str, *, markdown: str | None = None) -> dict[str, Any]:
    """Load the ticket PDF path and invoke the compiled graph."""
    pdf_path = load_ticket_pdf_path(ticket_id)
    payload: RfpIntakeState = {
        "ticket_id": ticket_id,
        "pdf_path": pdf_path,
        "markdown": markdown or "",
        "is_rfp": False,
        "discard_reason": None,
        "metadata": {},
        "extracts": {},
        "worker_results": {},
        "synthesizer": {},
        "phi_detected": False,
        "error_code": None,
    }
    try:
        return rfp_intake_graph.invoke(payload)
    except Exception:
        persist_pipeline_error(ticket_id)
        raise
