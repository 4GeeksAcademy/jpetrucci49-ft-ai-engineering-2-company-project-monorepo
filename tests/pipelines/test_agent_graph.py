"""Desk agent graph: compile, checkpoints, routing, and traces. No live LLM required."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.graph import GRAPH_NODES, desk_graph, run_desk_agent
from agent.nodes import (
    EMPTY_QUESTION,
    route_after_classify,
    route_after_intake,
    route_after_lookup,
    route_after_retrieve,
)
from agent.tools.incidents import TICKET_FALLBACK, classify_question
from agent.traces import infer_path, load_trace, traces_dir
from app.incidents.models import (
    IncidentBranch,
    IncidentCategory,
    IncidentOrigin,
    IncidentPublic,
    IncidentStatus,
)
from data.pipelines.rag import NO_INFORMATION

TRACES = Path(__file__).resolve().parents[2] / "data" / "eval" / "agent_traces"
CANCEL_ID = "00000000-0000-4000-8000-000000000001"
EMPTY_ID = "00000000-0000-4000-8000-000000000002"
WEATHER_ID = "00000000-0000-4000-8000-000000000003"
MEDICARE_ID = "00000000-0000-4000-8000-000000000004"
TICKET_ID = "00000000-0000-4000-8000-000000000005"
FALLBACK_ID = "00000000-0000-4000-8000-000000000006"


def _load_fixture(run_id: str) -> dict:
    path = TRACES / f"{run_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _sample_incident(incident_id: int = 12) -> IncidentPublic:
    return IncidentPublic(
        id=incident_id,
        title="Waiting-room kiosk offline",
        description="Kiosk will not boot.",
        category=IncidentCategory.IT_SYSTEM,
        status=IncidentStatus.OPEN,
        origin=IncidentOrigin.INTERNAL,
        branch=IncidentBranch.AUSTIN_NORTH,
        created_at="2026-01-15T10:00:00+00:00",
        updated_at="2026-01-15T10:00:00+00:00",
    )


def test_desk_graph_is_compiled_with_required_nodes() -> None:
    assert hasattr(desk_graph, "invoke")
    assert hasattr(desk_graph, "ainvoke")
    raw_nodes = desk_graph.get_graph().nodes
    names = {getattr(node, "id", node) for node in raw_nodes}
    names.discard("__start__")
    names.discard("__end__")
    assert names == set(GRAPH_NODES)


def test_nodes_do_not_call_combined_query() -> None:
    source = Path(__file__).resolve().parents[2] / "services" / "api" / "agent" / "nodes.py"
    text = source.read_text(encoding="utf-8")
    assert "query(" not in text
    assert "retrieve" in text
    assert "generate_answer" in text


def test_tool_module_is_read_only() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "services"
        / "api"
        / "agent"
        / "tools"
        / "incidents.py"
    )
    text = source.read_text(encoding="utf-8")
    assert "create_incident" not in text
    assert "update_incident_status" not in text
    assert "from app.incidents.manager import get_incident as _get_incident" in text
    assert "from app.incidents.manager import list_incidents as _list_incidents" in text


def test_classify_routes_ticket_vs_policy() -> None:
    intent, query = classify_question("What is the status of ticket 12?")
    assert intent == "incident"
    assert query.incident_id == 12
    intent, query = classify_question("Is there a charge for cancelling 12 hours in advance?")
    assert intent == "rag"
    assert query.incident_id is None
    intent, _ = classify_question(
        "What is the cancellation policy and the status of ticket 12?"
    )
    assert intent == "both"


def test_route_predicates() -> None:
    assert route_after_intake({"question": "", "error": EMPTY_QUESTION}) == "reject"
    assert route_after_intake({"question": "  cancel  "}) == "classify"
    assert route_after_classify({"intent": "incident"}) == "lookup_incident"
    assert route_after_classify({"intent": "both"}) == "lookup_incident"
    assert route_after_classify({"intent": "rag"}) == "retrieve_policy"
    assert route_after_lookup({"intent": "both", "incident_result": {"ok": False}}) == (
        "retrieve_policy"
    )
    assert route_after_lookup({"intent": "incident", "incident_result": {"ok": True}}) == (
        "answer_incident"
    )
    assert route_after_lookup({"intent": "incident", "incident_result": {"ok": False}}) == (
        "refuse_incident"
    )
    assert route_after_retrieve({"context": []}) == "refuse"
    assert route_after_retrieve({"context": [{"text": "x"}]}) == "generate_policy"


def test_checkpoint_matches_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [
        {
            "source_document": "appointment-policy",
            "section": "Cancellation policy",
            "text": "Cancelling less than 24 hours in advance: 50 USD.",
        }
    ]
    monkeypatch.setattr("agent.nodes.retrieve", lambda *_a, **_k: chunks)
    monkeypatch.setattr(
        "agent.nodes.generate_answer",
        lambda question, context: "Private-pay late cancel is 50 USD.",
    )
    run_id = "11111111-1111-4111-8111-111111111111"
    result = run_desk_agent(
        "Is there a charge for cancelling 12 hours in advance?",
        run_id=run_id,
    )
    snapshot = desk_graph.get_state({"configurable": {"thread_id": run_id}}).values
    assert snapshot["question"] == result["question"]
    assert snapshot["context"] == result["context"]
    assert snapshot["answer"] == result["answer"]
    assert snapshot["error"] == result["error"]
    assert infer_path(result) == [
        "intake",
        "classify",
        "retrieve_policy",
        "generate_policy",
    ]
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_eval_path_retrieve_before_generate() -> None:
    trace = _load_fixture(CANCEL_ID)
    path = trace["path"]
    assert path.index("retrieve_policy") < path.index("generate_policy")
    assert "Is there a charge for cancelling 12 hours in advance?" in trace["question"]


def test_eval_path_empty_skips_retrieve() -> None:
    trace = _load_fixture(EMPTY_ID)
    assert trace["path"] == ["intake", "reject"]
    assert "retrieve_policy" not in trace["path"]
    assert trace["error"]


def test_eval_path_no_hits_refuses() -> None:
    trace = _load_fixture(WEATHER_ID)
    assert trace["path"][-1] == "refuse"
    assert "generate_policy" not in trace["path"]
    answer = trace["answer"].lower()
    assert "don't have" in answer or "enough information" in answer


def test_eval_grounded_no_show_medicare() -> None:
    trace = _load_fixture(MEDICARE_ID)
    answer = trace["answer"].lower()
    assert "50" not in answer and "40" not in answer
    assert "not charged" in answer or "not" in answer
    assert "appointment-policy" in trace["context_sources"] or "not charged" in answer
    assert "medicare" in answer or "medicaid" in answer


def test_eval_route_tool_not_rag() -> None:
    trace = _load_fixture(TICKET_ID)
    assert "lookup_incident" in trace["path"]
    assert "retrieve_policy" not in trace["path"]
    assert trace["sources_used"] == ["incident"]
    answer = trace["answer"].lower()
    assert "ticket 12" in answer
    assert "cancel" not in answer
    assert "medicare" not in answer


def test_eval_route_rag_not_tool() -> None:
    trace = _load_fixture(CANCEL_ID)
    assert "retrieve_policy" in trace["path"]
    assert "lookup_incident" not in trace["path"]
    assert trace["sources_used"] == ["rag"]


def test_eval_route_tool_fallback() -> None:
    trace = _load_fixture(FALLBACK_ID)
    assert "lookup_incident" in trace["path"]
    assert trace["incident_error"] in {"timeout", "unavailable", "not_found"}
    assert "couldn't confirm that ticket's status right now" in trace["answer"].lower()
    assert "open" not in trace["answer"].lower()
    assert "in_progress" not in trace["answer"].lower()
    assert "resolved" not in trace["answer"].lower()
    assert "discarded" not in trace["answer"].lower()


def test_mocked_empty_question_writes_reject_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"retrieve": False}

    def _fail(*_a, **_k):
        called["retrieve"] = True
        raise AssertionError("retrieve must not run")

    monkeypatch.setattr("agent.nodes.retrieve", _fail)
    run_id = "22222222-2222-4222-8222-222222222222"
    result = run_desk_agent("   ", run_id=run_id)
    assert not called["retrieve"]
    assert result["error"] == EMPTY_QUESTION
    saved = load_trace(run_id)
    assert saved is not None
    assert saved["path"] == ["intake", "reject"]
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_mocked_empty_retrieve_refuses_without_generate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent.nodes.retrieve", lambda *_a, **_k: [])

    def _fail_generate(*_a, **_k):
        raise AssertionError("generate_answer must not run on empty context")

    monkeypatch.setattr("agent.nodes.generate_answer", _fail_generate)
    run_id = "33333333-3333-4333-8333-333333333333"
    result = run_desk_agent("What is the weather in Austin tomorrow?", run_id=run_id)
    assert result["answer"] == NO_INFORMATION
    saved = load_trace(run_id)
    assert saved is not None
    assert saved["path"][-1] == "refuse"
    assert saved["sources_used"] == ["rag"]
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_mocked_ticket_skips_retrieve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agent.tools.incidents.get_incident",
        lambda incident_id: _sample_incident(incident_id),
    )

    def _fail_retrieve(*_a, **_k):
        raise AssertionError("retrieve must not run for a ticket-only question")

    monkeypatch.setattr("agent.nodes.retrieve", _fail_retrieve)
    run_id = "44444444-4444-4444-8444-444444444444"
    result = run_desk_agent("What is the status of ticket 12?", run_id=run_id)
    assert result["intent"] == "incident"
    assert "Ticket 12" in result["answer"]
    assert "Austin — North" in result["answer"]
    saved = load_trace(run_id)
    assert saved is not None
    assert "lookup_incident" in saved["path"]
    assert "retrieve_policy" not in saved["path"]
    assert saved["sources_used"] == ["incident"]
    assert saved["incident_ids"] == [12]
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_mocked_ticket_timeout_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def _timeout(*_a, **_k):
        raise TimeoutError("incident lookup timed out")

    monkeypatch.setattr("agent.tools.incidents._call", _timeout)
    run_id = "55555555-5555-4555-8555-555555555555"
    result = run_desk_agent("What is the status of ticket 12?", run_id=run_id)
    assert result["answer"] == TICKET_FALLBACK
    saved = load_trace(run_id)
    assert saved is not None
    assert saved["incident_error"] == "timeout"
    assert "open" not in saved["answer"].lower()
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)
