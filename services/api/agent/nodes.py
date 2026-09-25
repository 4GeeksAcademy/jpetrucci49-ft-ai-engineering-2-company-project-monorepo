"""Graph nodes. retrieve_policy and generate_policy call 07.5 functions only."""

from __future__ import annotations

import uuid

from data.pipelines.rag import NO_INFORMATION, generate_answer, retrieve

from agent.state import DeskAgentState

EMPTY_QUESTION = "question must not be empty"


def intake(state: DeskAgentState) -> dict:
    run_id = state.get("run_id") or str(uuid.uuid4())
    question = (state.get("question") or "").strip()
    update: dict = {
        "run_id": run_id,
        "question": question,
        "context": [],
        "answer": "",
        "error": "",
    }
    if not question:
        update["error"] = EMPTY_QUESTION
    return update


def retrieve_policy(state: DeskAgentState) -> dict:
    return {"context": retrieve(state["question"], k=5)}


def generate_policy(state: DeskAgentState) -> dict:
    return {"answer": generate_answer(state["question"], state["context"])}


def refuse(_state: DeskAgentState) -> dict:
    return {"answer": NO_INFORMATION, "error": ""}


def reject(_state: DeskAgentState) -> dict:
    return {"error": EMPTY_QUESTION, "answer": ""}


def route_after_intake(state: DeskAgentState) -> str:
    if not (state.get("question") or "").strip():
        return "reject"
    return "retrieve_policy"


def route_after_retrieve(state: DeskAgentState) -> str:
    if not state.get("context"):
        return "refuse"
    return "generate_policy"
