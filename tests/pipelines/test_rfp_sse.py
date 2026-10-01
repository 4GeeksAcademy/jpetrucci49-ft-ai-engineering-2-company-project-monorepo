"""SSE notice when intake accepts an RFP ticket. No model calls."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@pytest.fixture()
def sse_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
        UserRegister(email="sse-listener@example.com", password="password123", name="SSE Listener")
    )
    headers = {"Authorization": f"Bearer {create_access_token(created.user.id)}"}

    from inventory.database import configure_engine, get_db, reset_engine
    import inventory.models  # noqa: F401
    import rfp.models  # noqa: F401
    import telemetry.table  # noqa: F401

    reset_engine()
    engine = configure_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_db():
        session = Session(engine, expire_on_commit=False, autoflush=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("rfp.service.RFP_RAW_DIR", tmp_path / "pdfs")
    monkeypatch.setattr("rfp.service.run_intake_job", lambda ticket_id: None)

    from rfp.events import reset_hub

    reset_hub()
    yield app, headers, engine
    app.dependency_overrides.pop(get_db, None)
    reset_hub()
    SQLModel.metadata.drop_all(engine)
    reset_engine()
    if auth_database._db is not None:
        auth_database._db.close()
        auth_database._db = None


def test_events_require_a_token(sse_api) -> None:
    app, _, _ = sse_api

    async def _request() -> int:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/rfp/events")
            return response.status_code

    assert asyncio.run(_request()) == 401


def test_stream_frame_after_ticket_accepted(sse_api) -> None:
    app, headers, engine = sse_api
    content_type, body, accepted = asyncio.run(
        asyncio.wait_for(_open_stream(app, headers, engine), timeout=10)
    )
    assert "text/event-stream" in content_type
    assert "event: rfp_ticket_created" in body
    assert "agent_status_changed" not in body
    payload = _data_payload(body)
    assert set(payload) == {
        "ticket_id",
        "rfp_id",
        "client_name",
        "client_country",
        "program_type",
        "status",
        "created_at",
    }
    assert payload["ticket_id"] == accepted["ticket_id"]
    assert payload["rfp_id"] == accepted["rfp_id"]
    assert payload["client_name"] == "Westbrook Manufacturing"
    assert payload["client_country"] == "US"
    assert payload["program_type"] == "occupational_health"
    assert payload["status"] == "analyzing"
    assert payload["created_at"].endswith("Z")


def test_discarded_ticket_is_listed_and_not_an_event(sse_api) -> None:
    app, headers, engine = sse_api
    import queue

    from rfp.events import subscribe, unsubscribe
    from rfp.service import create_ticket

    subscriber = subscribe()
    try:
        with Session(engine) as session:
            discarded = create_ticket(session, pdf_bytes=PDF, created_by="1")
        _discard(discarded.ticket_id)
        with pytest.raises(queue.Empty):
            subscriber.get_nowait()
    finally:
        unsubscribe(subscriber)

    accepted = _accept(engine)
    listed = asyncio.run(_list_tickets(app, headers))
    by_id = {row["ticket_id"]: row for row in listed["tickets"]}
    assert set(by_id[discarded.ticket_id]) == _NOTICE_FIELDS
    assert by_id[discarded.ticket_id]["status"] == "discarded"
    assert by_id[discarded.ticket_id]["rfp_id"] is None
    assert set(by_id[accepted["ticket_id"]]) == _NOTICE_FIELDS
    assert by_id[accepted["ticket_id"]]["status"] == "intake_complete"
    assert by_id[accepted["ticket_id"]]["client_name"] == "Westbrook Manufacturing"
    assert by_id[accepted["ticket_id"]]["rfp_id"] == accepted["rfp_id"]


_NOTICE_FIELDS = {
    "ticket_id",
    "rfp_id",
    "client_name",
    "client_country",
    "program_type",
    "status",
    "created_at",
}


async def _list_tickets(app, headers: dict[str, str]) -> dict:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/rfp/tickets", headers=headers)
        assert response.status_code == 200
        return response.json()


async def _open_stream(app, headers: dict[str, str], engine) -> tuple[str, str, dict]:
    """Read the live SSE response until persist_complete publishes one frame."""
    started = asyncio.Event()
    finished = asyncio.Event()
    response_headers: dict[str, str] = {}
    chunks: list[bytes] = []
    accepted: dict = {}

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/rfp/events",
        "raw_path": b"/rfp/events",
        "query_string": b"",
        "headers": [(b"authorization", headers["Authorization"].encode())],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }

    async def receive():
        await finished.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        if message["type"] == "http.response.start":
            response_headers.update(
                {key.decode().lower(): value.decode() for key, value in message["headers"]}
            )
            started.set()
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body") or b"")
            if b"event: rfp_ticket_created" in b"".join(chunks):
                finished.set()

    async def publish_once_open() -> None:
        await started.wait()
        accepted.update(await asyncio.to_thread(_accept, engine))

    stream = asyncio.create_task(app(scope, receive, send))
    publisher = asyncio.create_task(publish_once_open())
    await finished.wait()
    await publisher
    await stream
    return response_headers["content-type"], b"".join(chunks).decode(), accepted


def _accept(engine) -> dict[str, str]:
    from rfp.service import create_ticket

    with Session(engine) as session:
        created = create_ticket(session, pdf_bytes=PDF, created_by="1")
    from data.pipelines.rfp_intake.persist import persist_complete

    persist_complete(
        created.ticket_id,
        metadata={
            "client_name": "Westbrook Manufacturing",
            "client_country": "US",
            "program_type": "occupational_health",
        },
        worker_results={},
        handoff={},
        phi_detected=False,
    )
    with Session(engine) as session:
        from rfp.models import RfpTicket

        ticket = session.get(RfpTicket, created.ticket_id)
        assert ticket is not None
        assert ticket.rfp_id
        return {"ticket_id": ticket.ticket_id, "rfp_id": ticket.rfp_id}


def _discard(ticket_id: str) -> None:
    from data.pipelines.rfp_intake.persist import persist_discarded

    persist_discarded(ticket_id, "not_an_rfp")


def _data_payload(body: str) -> dict:
    data_lines = [
        line.removeprefix("data:").strip()
        for line in body.splitlines()
        if line.startswith("data:")
    ]
    return json.loads("\n".join(data_lines))
