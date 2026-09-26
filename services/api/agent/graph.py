"""Compile the desk agent once at import. Invoke never builds a new graph."""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    answer_incident,
    classify,
    generate_policy,
    intake,
    lookup_incident,
    refuse,
    refuse_incident,
    reject,
    retrieve_policy,
    route_after_classify,
    route_after_intake,
    route_after_lookup,
    route_after_retrieve,
)
from agent.state import DeskAgentState
from agent.traces import persist_trace

GRAPH_NODES = frozenset(
    {
        "intake",
        "classify",
        "lookup_incident",
        "answer_incident",
        "refuse_incident",
        "retrieve_policy",
        "generate_policy",
        "refuse",
        "reject",
    }
)


def build_desk_graph() -> StateGraph:
    builder = StateGraph(DeskAgentState)
    builder.add_node("intake", intake)
    builder.add_node("classify", classify)
    builder.add_node("lookup_incident", lookup_incident)
    builder.add_node("answer_incident", answer_incident)
    builder.add_node("refuse_incident", refuse_incident)
    builder.add_node("retrieve_policy", retrieve_policy)
    builder.add_node("generate_policy", generate_policy)
    builder.add_node("refuse", refuse)
    builder.add_node("reject", reject)
    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {"reject": "reject", "classify": "classify"},
    )
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {"lookup_incident": "lookup_incident", "retrieve_policy": "retrieve_policy"},
    )
    builder.add_conditional_edges(
        "lookup_incident",
        route_after_lookup,
        {
            "answer_incident": "answer_incident",
            "refuse_incident": "refuse_incident",
            "retrieve_policy": "retrieve_policy",
        },
    )
    builder.add_conditional_edges(
        "retrieve_policy",
        route_after_retrieve,
        {"refuse": "refuse", "generate_policy": "generate_policy"},
    )
    builder.add_edge("answer_incident", END)
    builder.add_edge("refuse_incident", END)
    builder.add_edge("refuse", END)
    builder.add_edge("reject", END)
    builder.add_edge("generate_policy", END)
    return builder


_checkpointer = MemorySaver()
desk_graph = build_desk_graph().compile(checkpointer=_checkpointer)


def _empty_state(run_id: str, question: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "question": question,
        "context": [],
        "answer": "",
        "error": "",
        "intent": "",
        "incident_query": {},
        "incident_result": {},
        "path": [],
    }


def run_desk_agent(question: str, *, run_id: str | None = None) -> dict[str, Any]:
    """Invoke the compiled graph, checkpoint, and persist a queryable trace."""
    run_id = run_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    result = desk_graph.invoke(_empty_state(run_id, question), config=config)
    persist_trace(result)
    return result
