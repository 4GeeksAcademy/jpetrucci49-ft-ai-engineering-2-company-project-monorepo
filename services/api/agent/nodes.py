"""Graph nodes. RAG, incidents, and inventory stay on separate nodes."""

from __future__ import annotations

import uuid

from data.pipelines.rag import NO_INFORMATION, generate_answer, retrieve

from agent.classify import classify_turn
from agent.memory.phi import PHI_REFUSAL, contains_phi
from agent.memory.propose import REMEMBER_PROMPT, looks_like_memory_intent, should_propose
from agent.memory.store import (
    format_notes,
    get_pending,
    log_phi_discard,
    propose,
    resolve,
    wrap_question,
)
from agent.state import DeskAgentState
from agent.tools.incidents import (
    TICKET_FALLBACK,
    IncidentLookupIn,
    lookup_incidents,
    ticket_sentence,
)
from agent.tools.inventory import (
    STOCK_FALLBACK,
    InventoryLookupIn,
    lookup_inventory as run_inventory_lookup,
    stock_sentence,
)

EMPTY_QUESTION = "question must not be empty"


def _step(name: str, **updates) -> dict:
    updates["path"] = [name]
    return updates


def _user_id(state: DeskAgentState) -> int:
    return int(state.get("user_id") or 0)


def _attach_tool_sentences(state: DeskAgentState, rag_answer: str) -> str:
    parts = [rag_answer]
    if state.get("intent") == "both":
        parts.append(ticket_sentence(state.get("incident_result") or {}))
    if state.get("intent") == "inventory_rag":
        parts.append(stock_sentence(state.get("inventory_result") or {}))
    return "\n\n".join(part for part in parts if part).strip()


def intake(state: DeskAgentState) -> dict:
    run_id = state.get("run_id") or str(uuid.uuid4())
    question = (state.get("question") or "").strip()
    user_id = _user_id(state)
    update: dict = {
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
        "memory_notes": format_notes(user_id),
        "memory_had_pending": get_pending(user_id) is not None,
        "memory_proposal_id": "",
        "memory_outcome": "",
    }
    if not question:
        update["error"] = EMPTY_QUESTION
    return _step("intake", **update)


def classify(state: DeskAgentState) -> dict:
    intent, incident_query, inventory_query = classify_turn(state["question"])
    return _step(
        "classify",
        intent=intent,
        incident_query=incident_query.model_dump(mode="json"),
        inventory_query=inventory_query.model_dump(mode="json"),
    )


def lookup_incident(state: DeskAgentState) -> dict:
    query = IncidentLookupIn.model_validate(state.get("incident_query") or {})
    result = lookup_incidents(query)
    return _step("lookup_incident", incident_result=result.model_dump(mode="json"))


def answer_incident(state: DeskAgentState) -> dict:
    return _step("answer_incident", answer=ticket_sentence(state.get("incident_result") or {}))


def refuse_incident(_state: DeskAgentState) -> dict:
    return _step("refuse_incident", answer=TICKET_FALLBACK)


def lookup_inventory(state: DeskAgentState) -> dict:
    query = InventoryLookupIn.model_validate(state.get("inventory_query") or {})
    result = run_inventory_lookup(query)
    return _step("lookup_inventory", inventory_result=result.model_dump(mode="json"))


def answer_inventory(state: DeskAgentState) -> dict:
    return _step("answer_inventory", answer=stock_sentence(state.get("inventory_result") or {}))


def refuse_inventory(_state: DeskAgentState) -> dict:
    return _step("refuse_inventory", answer=STOCK_FALLBACK)


def retrieve_policy(state: DeskAgentState) -> dict:
    return _step("retrieve_policy", context=retrieve(state["question"], k=5))


def generate_policy(state: DeskAgentState) -> dict:
    question = wrap_question(state["question"], state.get("memory_notes") or "")
    rag_answer = generate_answer(question, state["context"])
    return _step("generate_policy", answer=_attach_tool_sentences(state, rag_answer))


def refuse(state: DeskAgentState) -> dict:
    return _step(
        "refuse",
        answer=_attach_tool_sentences(state, NO_INFORMATION),
        error="",
    )


def reject(_state: DeskAgentState) -> dict:
    return _step("reject", error=EMPTY_QUESTION, answer="")


def resolve_memory(state: DeskAgentState) -> dict:
    user_id = _user_id(state)
    result = resolve(user_id, state.get("question") or "", run_id=state.get("run_id") or "")
    update: dict = {
        "memory_notes": format_notes(user_id),
        "memory_had_pending": False,
        "memory_proposal_id": result.proposal_id or "",
        "memory_outcome": result.outcome or "",
    }
    if result.phi_refusal:
        existing = (state.get("answer") or "").strip()
        update["answer"] = f"{existing}\n\n{PHI_REFUSAL}".strip()
    return _step("resolve_memory", **update)


def propose_memory(state: DeskAgentState) -> dict:
    user_id = _user_id(state)
    question = state.get("question") or ""
    answer = (state.get("answer") or "").strip()
    proposal_id = state.get("memory_proposal_id") or ""
    outcome = state.get("memory_outcome") or ""
    if get_pending(user_id) is not None:
        return _step(
            "propose_memory",
            memory_proposal_id=proposal_id,
            memory_outcome=outcome,
        )
    if contains_phi(question) and looks_like_memory_intent(question):
        proposal_id = log_phi_discard(
            user_id,
            run_id=state.get("run_id") or "",
            question=question,
        )
        return _step(
            "propose_memory",
            answer=_append_unique(answer, PHI_REFUSAL),
            memory_proposal_id=proposal_id,
            memory_outcome="discarded_phi",
        )
    proposal = should_propose(question, answer)
    if proposal is None:
        return _step(
            "propose_memory",
            memory_proposal_id=proposal_id,
            memory_outcome=outcome,
        )
    if contains_phi(proposal.text):
        proposal_id = log_phi_discard(
            user_id,
            run_id=state.get("run_id") or "",
            question=question,
        )
        return _step(
            "propose_memory",
            answer=_append_unique(answer, PHI_REFUSAL),
            memory_proposal_id=proposal_id,
            memory_outcome="discarded_phi",
        )
    pending = propose(
        user_id,
        proposal,
        run_id=state.get("run_id") or "",
        question=question,
    )
    return _step(
        "propose_memory",
        answer=_append_unique(answer, REMEMBER_PROMPT),
        memory_proposal_id=pending.proposal_id if pending else "",
        memory_outcome="",
    )


def _append_unique(answer: str, extra: str) -> str:
    if extra in answer:
        return answer
    if not answer:
        return extra
    return f"{answer}\n\n{extra}"


def route_after_intake(state: DeskAgentState) -> str:
    if not (state.get("question") or "").strip():
        return "reject"
    if state.get("memory_had_pending"):
        return "resolve_memory"
    return "classify"


def route_after_classify(state: DeskAgentState) -> str:
    intent = state.get("intent")
    if intent in {"incident", "both"}:
        return "lookup_incident"
    if intent in {"inventory", "inventory_rag"}:
        return "lookup_inventory"
    return "retrieve_policy"


def route_after_lookup(state: DeskAgentState) -> str:
    if state.get("intent") == "both":
        return "retrieve_policy"
    result = state.get("incident_result") or {}
    if result.get("ok"):
        return "answer_incident"
    return "refuse_incident"


def route_after_inventory(state: DeskAgentState) -> str:
    if state.get("intent") == "inventory_rag":
        return "retrieve_policy"
    result = state.get("inventory_result") or {}
    if result.get("ok"):
        return "answer_inventory"
    return "refuse_inventory"


def route_after_retrieve(state: DeskAgentState) -> str:
    if not state.get("context"):
        return "refuse"
    return "generate_policy"
