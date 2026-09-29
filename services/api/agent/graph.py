"""Compile the desk agent once at import. Invoke never builds a new graph."""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    answer_incident,
    answer_inventory,
    classify,
    generate_policy,
    guard_input,
    guard_output,
    intake,
    lookup_incident,
    lookup_inventory,
    propose_memory,
    refuse,
    refuse_incident,
    refuse_inventory,
    reject,
    resolve_memory,
    retrieve_policy,
    route_after_classify,
    route_after_guard_input,
    route_after_intake,
    route_after_inventory,
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
        "lookup_inventory",
        "answer_inventory",
        "refuse_inventory",
        "retrieve_policy",
        "generate_policy",
        "refuse",
        "reject",
        "resolve_memory",
        "propose_memory",
        "guard_input",
        "guard_output",
    }
)

_ANSWER_NODES = (
    "answer_incident",
    "refuse_incident",
    "answer_inventory",
    "refuse_inventory",
    "refuse",
    "generate_policy",
)


def build_desk_graph() -> StateGraph:
    builder = StateGraph(DeskAgentState)
    builder.add_node("intake", intake)
    builder.add_node("classify", classify)
    builder.add_node("lookup_incident", lookup_incident)
    builder.add_node("answer_incident", answer_incident)
    builder.add_node("refuse_incident", refuse_incident)
    builder.add_node("lookup_inventory", lookup_inventory)
    builder.add_node("answer_inventory", answer_inventory)
    builder.add_node("refuse_inventory", refuse_inventory)
    builder.add_node("retrieve_policy", retrieve_policy)
    builder.add_node("generate_policy", generate_policy)
    builder.add_node("refuse", refuse)
    builder.add_node("reject", reject)
    builder.add_node("resolve_memory", resolve_memory)
    builder.add_node("propose_memory", propose_memory)
    builder.add_node("guard_input", guard_input)
    builder.add_node("guard_output", guard_output)
    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "reject": "reject",
            "resolve_memory": "resolve_memory",
            "guard_input": "guard_input",
        },
    )
    builder.add_edge("resolve_memory", "guard_input")
    builder.add_conditional_edges(
        "guard_input",
        route_after_guard_input,
        {"classify": "classify", "end": END},
    )
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "lookup_incident": "lookup_incident",
            "lookup_inventory": "lookup_inventory",
            "retrieve_policy": "retrieve_policy",
        },
    )
    builder.add_conditional_edges(
        "lookup_inventory",
        route_after_inventory,
        {
            "answer_inventory": "answer_inventory",
            "refuse_inventory": "refuse_inventory",
            "retrieve_policy": "retrieve_policy",
        },
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
    for name in _ANSWER_NODES:
        builder.add_edge(name, "guard_output")
    builder.add_edge("guard_output", "propose_memory")
    builder.add_edge("propose_memory", END)
    builder.add_edge("reject", END)
    return builder


_checkpointer = MemorySaver()
desk_graph = build_desk_graph().compile(checkpointer=_checkpointer)


def _empty_state(run_id: str, question: str, user_id: int) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "question": question,
        "context": [],
        "answer": "",
        "error": "",
        "intent": "",
        "incident_query": {},
        "incident_result": {},
        "inventory_query": {},
        "inventory_result": {},
        "user_id": user_id,
        "memory_notes": "",
        "memory_had_pending": False,
        "memory_proposal_id": "",
        "memory_outcome": "",
        "input_label": "domain",
        "guardrail_name": "",
        "guardrail_blocked": False,
        "path": [],
    }


def run_desk_agent(
    question: str,
    *,
    user_id: int = 0,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Invoke the compiled graph, checkpoint, and persist a queryable trace."""
    run_id = run_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    result = desk_graph.invoke(_empty_state(run_id, question, user_id), config=config)
    persist_trace(result)
    return result
