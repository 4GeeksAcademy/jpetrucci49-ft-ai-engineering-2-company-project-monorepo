"""Desk agent graph: compile, checkpoints, routing, and traces. No live LLM required."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent.graph import GRAPH_NODES, desk_graph, run_desk_agent
from agent.classify import classify_turn
from agent.nodes import (
    EMPTY_QUESTION,
    route_after_classify,
    route_after_guard_input,
    route_after_intake,
    route_after_inventory,
    route_after_lookup,
    route_after_retrieve,
)
from agent.tools.incidents import TICKET_FALLBACK, classify_question
from agent.tools.inventory import STOCK_FALLBACK
from agent.traces import infer_path, load_trace, traces_dir
from inventory.schemas import MedicalSupplyResponse
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
GLOVES_ID = "00000000-0000-4000-8000-000000000007"
STOCK_FALLBACK_ID = "00000000-0000-4000-8000-000000000008"


def _load_fixture(run_id: str) -> dict:
    path = TRACES / f"{run_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _sample_supply() -> MedicalSupplyResponse:
    return MedicalSupplyResponse(
        id=1,
        name="Nitrile gloves (box of 100)",
        sku="HCR-PPE-001",
        category="ppe",
        unit="box",
        country="US",
        current_stock=40,
    )


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


@pytest.fixture(autouse=True)
def _isolate_agent_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(tmp_path / "agent_memory.json"))
    from agent.memory.store import reset_memory

    reset_memory()
    yield
    reset_memory()


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
    assert "from app.incidents.manager" not in text
    assert "call_incidents_get" in text


def test_inventory_tool_module_is_read_only() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "services"
        / "api"
        / "agent"
        / "tools"
        / "inventory.py"
    )
    text = source.read_text(encoding="utf-8")
    assert "create_supply" not in text
    assert "register_delivery" not in text
    assert "register_consumption" not in text
    assert "from inventory.service" not in text
    assert "call_inventory_query" in text


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


def test_classify_turn_routes_stock() -> None:
    intent, _, inventory_query = classify_turn("Do we have stock of nitrile gloves?")
    assert intent == "inventory"
    assert inventory_query.name_query and "nitrile" in inventory_query.name_query.lower()
    intent, _, _ = classify_turn(
        "What is the cancellation policy and do we have stock of nitrile gloves?"
    )
    assert intent == "inventory_rag"
    intent, _, _ = classify_turn("What is the status of ticket 12 and nitrile gloves?")
    assert intent == "incident"


def test_route_predicates() -> None:
    assert route_after_intake({"question": "", "error": EMPTY_QUESTION}) == "reject"
    assert route_after_intake({"question": "  cancel  "}) == "guard_input"
    assert route_after_guard_input({"guardrail_blocked": True}) == "end"
    assert route_after_guard_input({"guardrail_blocked": False}) == "classify"
    assert route_after_intake({"question": "yes", "memory_had_pending": True}) == (
        "resolve_memory"
    )
    assert route_after_classify({"intent": "incident"}) == "lookup_incident"
    assert route_after_classify({"intent": "both"}) == "lookup_incident"
    assert route_after_classify({"intent": "rag"}) == "retrieve_policy"
    assert route_after_classify({"intent": "inventory"}) == "lookup_inventory"
    assert route_after_classify({"intent": "inventory_rag"}) == "lookup_inventory"
    assert route_after_inventory(
        {"intent": "inventory", "inventory_result": {"ok": True}}
    ) == "answer_inventory"
    assert route_after_inventory(
        {"intent": "inventory", "inventory_result": {"ok": False}}
    ) == "refuse_inventory"
    assert route_after_inventory(
        {"intent": "inventory_rag", "inventory_result": {"ok": False}}
    ) == "retrieve_policy"
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
        "guard_input",
        "classify",
        "retrieve_policy",
        "generate_policy",
        "guard_output",
        "propose_memory",
    ]
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_eval_path_retrieve_before_generate() -> None:
    trace = _load_fixture(CANCEL_ID)
    path = trace["path"]
    assert path.index("retrieve_policy") < path.index("generate_policy")
    assert trace["intent"] == "rag"
    assert "question" not in trace
    assert "answer" not in trace


def test_eval_path_empty_skips_retrieve() -> None:
    trace = _load_fixture(EMPTY_ID)
    assert trace["path"] == ["intake", "reject"]
    assert "retrieve_policy" not in trace["path"]
    assert trace["error"]


def test_eval_path_no_hits_refuses() -> None:
    trace = _load_fixture(WEATHER_ID)
    assert trace["path"][-1] == "refuse"
    assert "generate_policy" not in trace["path"]
    assert trace["intent"] == "rag"
    assert trace["context_sources"] == []
    assert "answer" not in trace


def test_eval_grounded_no_show_medicare() -> None:
    trace = _load_fixture(MEDICARE_ID)
    path = trace["path"]
    assert path.index("retrieve_policy") < path.index("generate_policy")
    assert trace["intent"] == "rag"
    assert trace["context_sources"] == ["appointment-policy"]
    assert "answer" not in trace


def test_eval_route_tool_not_rag() -> None:
    trace = _load_fixture(TICKET_ID)
    assert "lookup_incident" in trace["path"]
    assert "retrieve_policy" not in trace["path"]
    assert trace["sources_used"] == ["incident"]
    assert trace["intent"] == "incident"
    assert trace["incident_ids"] == [12]
    assert "answer" not in trace


def test_eval_route_rag_not_tool() -> None:
    trace = _load_fixture(CANCEL_ID)
    assert "retrieve_policy" in trace["path"]
    assert "lookup_incident" not in trace["path"]
    assert "lookup_inventory" not in trace["path"]
    assert trace["sources_used"] == ["rag"]


def test_eval_route_inventory_not_rag() -> None:
    trace = _load_fixture(GLOVES_ID)
    assert "lookup_inventory" in trace["path"]
    assert "retrieve_policy" not in trace["path"]
    assert trace["sources_used"] == ["inventory"]
    assert trace["intent"] == "inventory"
    assert trace["supply_skus"] == ["HCR-PPE-001"]
    assert "answer" not in trace


def test_eval_route_rag_not_inventory() -> None:
    trace = _load_fixture(CANCEL_ID)
    assert "lookup_inventory" not in trace["path"]
    assert "inventory" not in trace["sources_used"]


def test_eval_route_inventory_fallback() -> None:
    trace = _load_fixture(STOCK_FALLBACK_ID)
    assert "lookup_inventory" in trace["path"]
    assert "refuse_inventory" in trace["path"]
    assert trace["inventory_error"] in {"timeout", "unavailable", "not_found"}
    assert trace["supply_skus"] == []
    assert "answer" not in trace


def test_eval_route_tool_fallback() -> None:
    trace = _load_fixture(FALLBACK_ID)
    assert "lookup_incident" in trace["path"]
    assert "refuse_incident" in trace["path"]
    assert trace["incident_error"] in {"timeout", "unavailable", "not_found"}
    assert trace["incident_ids"] == []
    assert "answer" not in trace


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
    result = run_desk_agent(
        "What is the HIPAA breach notification window for US clinics?",
        run_id=run_id,
    )
    assert result["answer"] == NO_INFORMATION
    saved = load_trace(run_id)
    assert saved is not None
    assert saved["path"][-1] == "propose_memory"
    assert "refuse" in saved["path"]
    assert saved["sources_used"] == ["rag"]
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_mocked_ticket_skips_retrieve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agent.tools.incidents.call_incidents_get",
        lambda incident_id: _sample_incident(incident_id).model_dump(mode="json"),
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
    assert "question" not in saved
    assert "answer" not in saved
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_mocked_stock_skips_retrieve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agent.tools.inventory.call_inventory_query",
        lambda **_k: {"ok": True, "supplies": [_sample_supply().model_dump(mode="json")]},
    )

    def _fail_retrieve(*_a, **_k):
        raise AssertionError("retrieve must not run for a stock-only question")

    monkeypatch.setattr("agent.nodes.retrieve", _fail_retrieve)
    run_id = "66666666-6666-4666-8666-666666666666"
    result = run_desk_agent("Do we have stock of nitrile gloves?", run_id=run_id)
    assert result["intent"] == "inventory"
    assert "40" in result["answer"]
    assert "HCR-PPE-001" in result["answer"]
    saved = load_trace(run_id)
    assert saved is not None
    assert "lookup_inventory" in saved["path"]
    assert "retrieve_policy" not in saved["path"]
    assert saved["sources_used"] == ["inventory"]
    assert saved["supply_skus"] == ["HCR-PPE-001"]
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_mocked_stock_timeout_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def _timeout(*_a, **_k):
        raise TimeoutError("inventory lookup timed out")

    monkeypatch.setattr("agent.tools.inventory._call", _timeout)
    run_id = "77777777-7777-4777-8777-777777777777"
    result = run_desk_agent("Do we have stock of nitrile gloves?", run_id=run_id)
    assert result["answer"] == STOCK_FALLBACK
    saved = load_trace(run_id)
    assert saved is not None
    assert saved["inventory_error"] == "timeout"
    assert "question" not in saved
    assert "answer" not in saved
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_build_trace_omits_question_and_answer() -> None:
    from agent.traces import build_trace

    payload = build_trace(
        {
            "run_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "path": ["intake", "guard_input", "classify", "retrieve_policy"],
            "question": "synthetic staff question",
            "answer": "synthetic answer text",
            "intent": "rag",
            "error": "",
            "guardrail_name": "output_leak",
        }
    )
    assert payload["intent"] == "rag"
    assert payload["guardrail"] == {"type": "security", "name": "output_leak"}
    blob = json.dumps(payload)
    assert "question" not in payload
    assert "answer" not in payload
    assert "synthetic staff question" not in blob
    assert "synthetic answer text" not in blob


def test_agent_query_rate_limit_does_not_call_the_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    from agent.rate_limit import RATE_LIMIT_DETAIL, reset_agent_query_limits
    from agent.router import AgentQueryIn, agent_query
    from auth.models import UserPublic, UserRole

    reset_agent_query_limits()
    clock = {"t": 1_000.0}
    monkeypatch.setattr("agent.rate_limit._now", lambda: clock["t"])
    calls = {"n": 0}

    def _fake(question: str, user_id: int | None = None):
        calls["n"] += 1
        return {
            "answer": "policy line",
            "run_id": "99999999-9999-4999-8999-999999999999",
            "error": "",
        }

    monkeypatch.setattr("agent.router.run_desk_agent", _fake)
    question = "What is the cancellation charge for a private-pay visit?"
    user = UserPublic(
        id=7,
        email="desk-limit@example.com",
        is_active=True,
        role=UserRole.user,
        created_at=datetime.now(timezone.utc),
    )
    other = user.model_copy(update={"id": 8})
    for _ in range(10):
        agent_query(AgentQueryIn(question=question), user)
    with pytest.raises(HTTPException) as exc:
        agent_query(AgentQueryIn(question=question), user)
    assert exc.value.status_code == 429
    assert exc.value.detail == RATE_LIMIT_DETAIL
    assert question not in str(exc.value.detail)
    assert calls["n"] == 10
    agent_query(AgentQueryIn(question=question), other)
    assert calls["n"] == 11
    clock["t"] = 1_061.0
    agent_query(AgentQueryIn(question=question), user)
    assert calls["n"] == 12
    reset_agent_query_limits()


def test_agent_incidents_via_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    root = Path(__file__).resolve().parents[2]
    nodes = (root / "services" / "api" / "agent" / "nodes.py").read_text(encoding="utf-8")
    tools = (
        root / "services" / "api" / "agent" / "tools" / "incidents.py"
    ).read_text(encoding="utf-8")
    assert "from app.incidents.manager" not in nodes
    assert "from app.incidents.manager" not in tools
    monkeypatch.setattr(
        "agent.tools.incidents.call_incidents_get",
        lambda incident_id: _sample_incident(incident_id).model_dump(mode="json"),
    )
    run_id = "88888888-8888-4888-8888-888888888888"
    result = run_desk_agent("What is the status of ticket 12?", run_id=run_id)
    assert "lookup_incident" in infer_path(result)
    assert "Ticket 12" in result["answer"]
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_mcp_inventory_mutate_rejected() -> None:
    from mcps.healthcore.tools.inventory import inventory_mutate

    source = (
        Path(__file__).resolve().parents[2]
        / "mcps"
        / "healthcore"
        / "tools"
        / "inventory.py"
    )
    text = source.read_text(encoding="utf-8")
    assert "create_supply" not in text
    assert "register_delivery" not in text
    assert "register_consumption" not in text
    result = inventory_mutate(supply_id=1, sku="HCR-PPE-001", quantity=5, action="consume")
    assert result["ok"] is False
    assert result["error"] == "inventory_read_only"


def _fake_auth_server():
    from mcpauth.config import AuthServerConfig, AuthServerType, AuthorizationServerMetadata

    return AuthServerConfig(
        type=AuthServerType.OIDC,
        metadata=AuthorizationServerMetadata(
            issuer="https://auth.example.test/oidc",
            authorization_endpoint="https://auth.example.test/oidc/auth",
            token_endpoint="https://auth.example.test/oidc/token",
            jwks_uri="https://auth.example.test/oidc/jwks",
            response_types_supported=["code"],
            code_challenge_methods_supported=["S256"],
        ),
    )


def test_mcp_http_rejects_missing_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_RESOURCE", "https://example.test/mcp")
    monkeypatch.setenv("MCP_AUTH_ISSUER", "https://auth.example.test/oidc")
    from starlette.testclient import TestClient

    from mcps.healthcore.server import create_app

    app = create_app(_fake_auth_server())
    with TestClient(app) as client:
        prm = client.get("/.well-known/oauth-protected-resource/mcp")
        denied = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert prm.status_code == 200
    assert "incidents:read" in prm.json()["scopes_supported"]
    assert "inventory:write" not in (prm.json().get("scopes_supported") or [])
    assert denied.status_code == 401
    assert "WWW-Authenticate" in denied.headers
