"""Desk agent graph: compile, checkpoints, and trace evals. No live LLM required."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.graph import GRAPH_NODES, desk_graph, run_desk_agent
from agent.nodes import EMPTY_QUESTION, route_after_intake, route_after_retrieve
from agent.traces import infer_path, load_trace, traces_dir
from data.pipelines.rag import NO_INFORMATION

TRACES = Path(__file__).resolve().parents[2] / "data" / "eval" / "agent_traces"
CANCEL_ID = "00000000-0000-4000-8000-000000000001"
EMPTY_ID = "00000000-0000-4000-8000-000000000002"
WEATHER_ID = "00000000-0000-4000-8000-000000000003"
MEDICARE_ID = "00000000-0000-4000-8000-000000000004"


def _load_fixture(run_id: str) -> dict:
    path = TRACES / f"{run_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


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


def test_route_predicates() -> None:
    assert route_after_intake({"question": "", "error": EMPTY_QUESTION}) == "reject"
    assert route_after_intake({"question": "  cancel  "}) == "retrieve_policy"
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
    assert infer_path(result) == ["intake", "retrieve_policy", "generate_policy"]
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
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)
