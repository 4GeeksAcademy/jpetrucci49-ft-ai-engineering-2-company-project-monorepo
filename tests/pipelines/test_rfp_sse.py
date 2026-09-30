"""SSE notice when an RFP ticket row is committed. No model calls."""

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


def test_stream_frame_after_create_ticket(sse_api) -> None:
    app, headers, engine = sse_api
    content_type, body = asyncio.run(asyncio.wait_for(_open_stream(app, headers, engine), timeout=10))
    assert "text/event-stream" in content_type
    assert "event: rfp_ticket_created" in body
    payload = _data_payload(body)
    assert set(payload) == {"ticket_id", "status", "agent_id", "flow_type"}
    assert payload["status"] == "analyzing"
    assert payload["agent_id"] == "rfp_pipeline"
    assert payload["flow_type"] == "rfp_workflow"
    assert payload["ticket_id"]


def test_ticket_created_with_no_subscriber_is_listed(sse_api) -> None:
    app, headers, engine = sse_api
    from rfp.service import create_ticket

    with Session(engine) as session:
        created = create_ticket(session, pdf_bytes=PDF, created_by="1")

    async def _request() -> dict:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/rfp/tickets", headers=headers)
            assert response.status_code == 200
            return response.json()

    body = asyncio.run(_request())
    assert body["tickets"]
    notice = next(row for row in body["tickets"] if row["ticket_id"] == created.ticket_id)
    assert notice == {"ticket_id": created.ticket_id, "status": "analyzing"}


async def _open_stream(app, headers: dict[str, str], engine) -> tuple[str, str]:
    """Read the live SSE response until create_ticket publishes one frame."""
    started = asyncio.Event()
    finished = asyncio.Event()
    response_headers: dict[str, str] = {}
    chunks: list[bytes] = []

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
        await asyncio.to_thread(_create_ticket, engine)

    stream = asyncio.create_task(app(scope, receive, send))
    publisher = asyncio.create_task(publish_once_open())
    await finished.wait()
    await publisher
    await stream
    return response_headers["content-type"], b"".join(chunks).decode()


def _create_ticket(engine) -> None:
    from rfp.service import create_ticket

    with Session(engine) as session:
        create_ticket(session, pdf_bytes=PDF, created_by="1")


def _data_payload(body: str) -> dict:
    data_lines = [
        line.removeprefix("data:").strip()
        for line in body.splitlines()
        if line.startswith("data:")
    ]
    return json.loads("\n".join(data_lines))
