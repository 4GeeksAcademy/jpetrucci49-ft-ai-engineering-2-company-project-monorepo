"""Compiled ``rfp_draft`` graph. Dedicated — not ``desk_graph`` or ``rfp_intake_graph``."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from data.pipelines.rfp_draft.nodes import (
    assign_node,
    combine_eval_node,
    dispatch_revise_node,
    eval_compliance_node,
    eval_readability_node,
    eval_relevance_node,
    generate_clinical_node,
    generate_compliance_node,
    generate_revenue_node,
    mark_under_evaluation_node,
    persist_node,
    route_after_combine,
)
from data.pipelines.rfp_draft.persist import persist_draft_pipeline_error
from data.pipelines.rfp_draft.state import RfpDraftState

GRAPH_NODES = frozenset(
    {
        "assign",
        "generate_revenue",
        "generate_clinical",
        "generate_compliance",
        "mark_under_evaluation",
        "eval_readability",
        "eval_relevance",
        "eval_compliance",
        "combine_eval",
        "dispatch_revise",
        "persist",
    }
)


def build_rfp_draft_graph() -> StateGraph:
    builder = StateGraph(RfpDraftState)
    builder.add_node("assign", assign_node)
    builder.add_node("generate_revenue", generate_revenue_node)
    builder.add_node("generate_clinical", generate_clinical_node)
    builder.add_node("generate_compliance", generate_compliance_node)
    builder.add_node("mark_under_evaluation", mark_under_evaluation_node)
    builder.add_node("eval_readability", eval_readability_node)
    builder.add_node("eval_relevance", eval_relevance_node)
    builder.add_node("eval_compliance", eval_compliance_node)
    builder.add_node("combine_eval", combine_eval_node)
    builder.add_node("dispatch_revise", dispatch_revise_node)
    builder.add_node("persist", persist_node)

    builder.add_edge(START, "assign")
    builder.add_edge("assign", "generate_revenue")
    builder.add_edge("assign", "generate_clinical")
    builder.add_edge("assign", "generate_compliance")
    builder.add_edge("generate_revenue", "mark_under_evaluation")
    builder.add_edge("generate_clinical", "mark_under_evaluation")
    builder.add_edge("generate_compliance", "mark_under_evaluation")
    builder.add_edge("mark_under_evaluation", "eval_readability")
    builder.add_edge("mark_under_evaluation", "eval_relevance")
    builder.add_edge("mark_under_evaluation", "eval_compliance")
    builder.add_edge("eval_readability", "combine_eval")
    builder.add_edge("eval_relevance", "combine_eval")
    builder.add_edge("eval_compliance", "combine_eval")
    builder.add_conditional_edges(
        "combine_eval",
        route_after_combine,
        {"dispatch_revise": "dispatch_revise", "persist": "persist"},
    )
    builder.add_edge("dispatch_revise", "generate_revenue")
    builder.add_edge("dispatch_revise", "generate_clinical")
    builder.add_edge("dispatch_revise", "generate_compliance")
    builder.add_edge("persist", END)
    return builder


rfp_draft_graph = build_rfp_draft_graph().compile()


def run_rfp_draft(ticket_id: str) -> dict[str, Any]:
    """Load Part 1 handoff from the ticket and invoke the compiled draft graph."""
    payload: RfpDraftState = {
        "ticket_id": ticket_id,
        "handoff": {},
        "iteration": {},
        "drafts": {},
        "eval_parts": {},
        "results": {},
        "feedback": {},
        "pending": [],
        "error_code": None,
    }
    try:
        return rfp_draft_graph.invoke(payload)
    except Exception:
        persist_draft_pipeline_error(ticket_id)
        raise
