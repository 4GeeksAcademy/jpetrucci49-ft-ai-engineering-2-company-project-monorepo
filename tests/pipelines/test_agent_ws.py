"""Desk chat WebSocket: token deltas, abort, and session rehydrate. No live model."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture()
def chat_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HEALTHCORE_API_TEST", "1")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-unit-testsie")
    from app.main import app

    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-unit-testsie")
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.json"))
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)

    import auth.database as auth_database

    if auth_database._db is not None:
        auth_database._db.close()
    auth_database._db = None

    from auth.models import UserRegister
    from auth.security import create_access_token
    from auth.services.users import create_user

    created = create_user(
        UserRegister(email="desk-chat@example.com", password="password123", name="Desk Chat")
    )
    token = create_access_token(created.user.id)

    from agent.chat import reset_chat_sessions

    reset_chat_sessions()
    with TestClient(app) as client:
        yield client, token
    reset_chat_sessions()
    if auth_database._db is not None:
        auth_database._db.close()
        auth_database._db = None


def test_chat_rejects_a_missing_token(chat_api) -> None:
    client, _ = chat_api
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/agent/chat?session_id=session-1") as ws:
            ws.send_json({"event": "user_message", "data": {"session_id": "session-1", "text": "Hello"}})
            ws.receive_json()


def test_user_message_streams_then_completes(chat_api, monkeypatch: pytest.MonkeyPatch) -> None:
    client, token = chat_api
    monkeypatch.setattr("agent.chat.produce_answer", _quick_answer)
    with client.websocket_connect(_url("session-ok", token)) as ws:
        history = ws.receive_json()
        assert history["event"] == "session_snapshot"
        assert history["data"]["session_id"] == "session-ok"
        assert history["data"]["messages"] == []
        assert "ticket_id" not in history["data"]
        ws.send_json(
            {
                "event": "user_message",
                "data": {"session_id": "session-ok", "text": "What is the cancellation charge?"},
            }
        )
        frames = _until(ws, "generation_completed")
    chunks = [frame for frame in frames if frame["event"] == "token_chunk"]
    assert [frame["data"]["token"] for frame in chunks] == ["Pol", "icy"]
    assert [frame["data"]["sequence"] for frame in chunks] == [1, 2]
    completed = frames[-1]
    assert completed["data"]["message_id"]
    assert "text" not in completed["data"]
    assert "ticket_id" not in completed["data"]


def test_interrupt_stops_tokens_and_starts_a_new_turn(
    chat_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, token = chat_api
    monkeypatch.setattr("agent.chat.produce_answer", _interruptible_answer)
    with client.websocket_connect(_url("session-stop", token)) as ws:
        ws.receive_json()
        ws.send_json({"event": "user_message", "data": {"session_id": "session-stop", "text": "First question"}})
        _until(ws, "token_chunk")
        ws.send_json(
            {
                "event": "interrupt_requested",
                "data": {"session_id": "session-stop", "new_input": "Ask about referrals instead"},
            }
        )
        rest = _until(ws, "generation_completed")
    interrupted = next(frame for frame in rest if frame["event"] == "generation_interrupted")
    assert interrupted["data"]["status"] == "interrupted"
    assert interrupted["data"]["message_id"]
    assert rest[0]["event"] == "generation_interrupted"
    next_chunks = [frame for frame in rest if frame["event"] == "token_chunk"]
    assert [frame["data"]["sequence"] for frame in next_chunks] == [1]
    completed = rest[-1]
    assert completed["data"]["message_id"] != interrupted["data"]["message_id"]


def test_two_sockets_share_one_generation(chat_api, monkeypatch: pytest.MonkeyPatch) -> None:
    client, token = chat_api
    _SHARED_CALLS.clear()
    _SHARED_STARTED.clear()
    _SHARED_RELEASE.clear()
    monkeypatch.setattr("agent.chat.produce_answer", _shared_answer)
    with client.websocket_connect(_url("session-shared", token)) as first:
        first.receive_json()
        first.send_json(
            {"event": "user_message", "data": {"session_id": "session-shared", "text": "Shared question"}}
        )
        assert _SHARED_STARTED.wait(timeout=2)
        with client.websocket_connect(_url("session-shared", token)) as second:
            second.receive_json()
            _SHARED_RELEASE.set()
            first_frames = _until(first, "generation_completed")
            second_frames = _until(second, "generation_completed")
    assert _SHARED_CALLS == ["Shared question"]
    assert [frame["data"]["token"] for frame in first_frames if frame["event"] == "token_chunk"] == ["A", "B"]
    assert [frame["data"]["token"] for frame in second_frames if frame["event"] == "token_chunk"] == ["A", "B"]


def test_reconnect_restores_the_interrupted_message(
    chat_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, token = chat_api
    monkeypatch.setattr("agent.chat.produce_answer", _interruptible_answer)
    with client.websocket_connect(_url("session-again", token)) as ws:
        ws.receive_json()
        ws.send_json({"event": "user_message", "data": {"session_id": "session-again", "text": "First question"}})
        _until(ws, "token_chunk")
        ws.send_json(
            {"event": "interrupt_requested", "data": {"session_id": "session-again", "new_input": ""}}
        )
        _until(ws, "generation_interrupted")
    with client.websocket_connect(_url("session-again", token)) as ws:
        history = ws.receive_json()
    assert history["event"] == "session_snapshot"
    assistant = next(row for row in history["data"]["messages"] if row["role"] == "assistant")
    assert assistant["status"] == "interrupted"
    assert assistant["text"]


def test_streaming_completion_stops_when_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("data.pipelines.rag.chat_model_candidates", lambda: ["test-model"])
    monkeypatch.setattr("data.pipelines.rag.rag_api_key", lambda: "test-key")
    monkeypatch.setattr("data.pipelines.rag.rag_base_url", lambda: "http://llm.test/v1")
    cancel = threading.Event()
    seen: list[str] = []

    class _Body:
        status_code = 200
        is_error = False
        text = ""

        def iter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
            cancel.set()
            yield 'data: {"choices":[{"delta":{"content":" there"}}]}'

        def read(self):
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def stream(self, method, url, headers=None, json=None):
            assert json["stream"] is True
            return _Body()

    monkeypatch.setattr("data.pipelines.rag.httpx.Client", _Client)
    from data.pipelines.rag import (
        generate_answer,
        reset_stream_cancel,
        reset_stream_sink,
        set_stream_cancel,
        set_stream_sink,
    )

    sink_token = set_stream_sink(seen.append)
    cancel_token = set_stream_cancel(cancel)
    try:
        text = generate_answer("question", [{"text": "policy", "source_document": "a", "section": "b"}])
    finally:
        reset_stream_sink(sink_token)
        reset_stream_cancel(cancel_token)
    assert text == "Hi"
    assert seen == ["Hi"]


_SHARED_STARTED = threading.Event()
_SHARED_RELEASE = threading.Event()
_SHARED_CALLS: list[str] = []


def _quick_answer(question: str, *, user_id: int, session_id: str, sink, cancel: threading.Event) -> str:
    del question, user_id, session_id, cancel
    sink("Pol")
    sink("icy")
    return "Policy"


def _interruptible_answer(
    question: str, *, user_id: int, session_id: str, sink, cancel: threading.Event
) -> str:
    del user_id, session_id
    if question != "First question":
        sink("Next")
        return "Next"
    sink("Hel")
    for _ in range(100):
        if cancel.is_set():
            return "Hel"
        threading.Event().wait(0.01)
    sink("lo")
    return "Hello"


def _shared_answer(question: str, *, user_id: int, session_id: str, sink, cancel: threading.Event) -> str:
    del user_id, session_id, cancel
    _SHARED_CALLS.append(question)
    _SHARED_STARTED.set()
    assert _SHARED_RELEASE.wait(timeout=2)
    sink("A")
    sink("B")
    return "AB"


def _url(session_id: str, token: str) -> str:
    return f"/agent/chat?session_id={session_id}&token={token}"


def _until(ws, event_type: str, limit: int = 20) -> list[dict]:
    frames: list[dict] = []
    for _ in range(limit):
        frame = ws.receive_json()
        frames.append(frame)
        if frame.get("event") == event_type:
            return frames
    raise AssertionError(frames)
