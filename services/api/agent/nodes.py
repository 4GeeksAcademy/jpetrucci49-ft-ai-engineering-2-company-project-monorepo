"""Graph nodes. RAG and incident lookup stay on separate nodes."""

from __future__ import annotations

import uuid

from data.pipelines.rag import NO_INFORMATION, generate_answer, retrieve

from agent.state import DeskAgentState
from agent.tools.incidents import (
    TICKET_FALLBACK,
    IncidentLookupIn,
    classify_question,
    lookup_incidents,
    ticket_sentence,
)

EMPTY_QUESTION = "question must not be empty"


def _step(name: str, **updates) -> dict:
    updates["path"] = [name]
    return updates


def _attach_ticket_if_both(state: DeskAgentState, rag_answer: str) -> str:
    if state.get("intent") != "both":
        return rag_answer
    extra = ticket_sentence(state.get("incident_result") or {})
    return f"{rag_answer}\n\n{extra}".strip()


def intake(state: DeskAgentState) -> dict:
    run_id = state.get("run_id") or str(uuid.uuid4())
    question = (state.get("question") or "").strip()
    update: dict = {
        "run_id": run_id,
        "question": question,
        "context": [],
        "answer": "",
        "error": "",
        "intent": "",
        "incident_query": {},
        "incident_result": {},
    }
    if not question:
        update["error"] = EMPTY_QUESTION
    return _step("intake", **update)


def classify(state: DeskAgentState) -> dict:
    intent, query = classify_question(state["question"])
    return _step(
        "classify",
        intent=intent,
        incident_query=query.model_dump(mode="json"),
    )


def lookup_incident(state: DeskAgentState) -> dict:
    query = IncidentLookupIn.model_validate(state.get("incident_query") or {})
    result = lookup_incidents(query)
    return _step("lookup_incident", incident_result=result.model_dump(mode="json"))


def answer_incident(state: DeskAgentState) -> dict:
    return _step("answer_incident", answer=ticket_sentence(state.get("incident_result") or {}))


def refuse_incident(_state: DeskAgentState) -> dict:
    return _step("refuse_incident", answer=TICKET_FALLBACK)


def retrieve_policy(state: DeskAgentState) -> dict:
    return _step("retrieve_policy", context=retrieve(state["question"], k=5))


def generate_policy(state: DeskAgentState) -> dict:
    rag_answer = generate_answer(state["question"], state["context"])
    return _step("generate_policy", answer=_attach_ticket_if_both(state, rag_answer))


def refuse(state: DeskAgentState) -> dict:
    return _step(
        "refuse",
        answer=_attach_ticket_if_both(state, NO_INFORMATION),
        error="",
    )


def reject(_state: DeskAgentState) -> dict:
    return _step("reject", error=EMPTY_QUESTION, answer="")


def route_after_intake(state: DeskAgentState) -> str:
    if not (state.get("question") or "").strip():
        return "reject"
    return "classify"


def route_after_classify(state: DeskAgentState) -> str:
    if state.get("intent") in {"incident", "both"}:
        return "lookup_incident"
    return "retrieve_policy"


def route_after_lookup(state: DeskAgentState) -> str:
    if state.get("intent") == "both":
        return "retrieve_policy"
    result = state.get("incident_result") or {}
    if result.get("ok"):
        return "answer_incident"
    return "refuse_incident"


def route_after_retrieve(state: DeskAgentState) -> str:
    if not state.get("context"):
        return "refuse"
    return "generate_policy"
