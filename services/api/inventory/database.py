"""PostgreSQL engine and per-request session for medical supply inventory.

Auth remains on TinyDB. This module is the only inventory connection to Supabase
(or a local SQLite URL for development/tests).
"""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Generator
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _is_test_environment() -> bool:
    return os.getenv("HEALTHCORE_API_TEST", "").strip().lower() in {"1", "true", "yes"}


def load_local_env() -> None:
    """Fill missing os.environ keys from services/api/.env (does not override)."""
    if not _ENV_FILE.is_file():
        return
    for raw_line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def get_database_url() -> str:
    if not _is_test_environment():
        load_local_env()
    url = os.getenv("SUPABASE_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "SUPABASE_DATABASE_URL is not set. Copy services/api/.env.example to .env "
            "and set a postgresql+psycopg:// Session pooler URI "
            "(or sqlite:///./inventory.db for local dev)."
        )
    return url


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return _ensure_sslmode(url)


def _ensure_sslmode(url: str) -> str:
    if url.startswith("sqlite") or "sslmode=" in url:
        return url
    if "supabase.co" not in url and "pooler.supabase.com" not in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}sslmode=require"


_CREDENTIAL_URL = re.compile(r"(?:postgres(?:ql)?(?:\+[\w]+)?://)[^\s\"']+", re.IGNORECASE)


def redact_secrets(text: str) -> str:
    """Strip connection URIs and password query params from operator-facing errors."""
    redacted = _CREDENTIAL_URL.sub("postgresql+psycopg://***", text)
    return re.sub(r"(?i)password=[^&\s]+", "password=***", redacted)


def connection_error_hint(exc: BaseException) -> str | None:
    """Operator hint for common Supabase / Codespaces connectivity failures."""
    text = str(exc).lower()
    if "network is unreachable" in text or "cannot assign requested address" in text:
        return (
            "The database host resolved to IPv6, which this environment cannot reach. "
            "Use the Supabase Session pooler URI (Connect → Session pooler): "
            "user postgres.<project-ref>, host aws-0-<region>.pooler.supabase.com, "
            "port 5432, and sslmode=require. Direct db.<project-ref>.supabase.co "
            "hosts are IPv6-only on many plans."
        )
    if "password authentication failed" in text:
        return "Check the database password and that the username is postgres.<project-ref> for the pooler."
    if "ssl" in text:
        return "Supabase requires TLS. Append ?sslmode=require to SUPABASE_DATABASE_URL."
    return None


def _engine_kwargs(url: str) -> dict:
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        return kwargs
    if "pooler.supabase.com" in url or ":6543/" in url:
        kwargs["connect_args"] = {"prepare_threshold": None}
    return kwargs


def _register_sqlite3_datetime_adapters() -> None:
    """Replace Python 3.12's deprecated default date/datetime sqlite3 adapters."""

    def adapt_date(value: date) -> str:
        return value.isoformat()

    def adapt_datetime(value: datetime) -> str:
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.isoformat(sep=" ", timespec="microseconds")

    sqlite3.register_adapter(date, adapt_date)
    sqlite3.register_adapter(datetime, adapt_datetime)


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    _register_sqlite3_datetime_adapters()

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def configure_engine(
    url: str,
    *,
    connect_args: dict | None = None,
    poolclass: type | None = None,
) -> Engine:
    """Create (or replace) the process engine. Used at startup and in tests."""
    global _engine, _SessionLocal

    reset_engine()
    normalized = _normalize_database_url(url)
    kwargs = _engine_kwargs(normalized)
    if connect_args is not None:
        kwargs["connect_args"] = connect_args
    if poolclass is not None:
        kwargs["poolclass"] = poolclass

    _engine = create_engine(normalized, **kwargs)
    _enable_sqlite_foreign_keys(_engine)
    _SessionLocal = sessionmaker(
        bind=_engine,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
    )
    return _engine


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_engine() -> Engine:
    if _engine is None:
        configure_engine(get_database_url())
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield one SQLModel session per request. Commit on success, rollback on error."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_inventory_schema() -> None:
    """Create tables if missing. Skip when tests have no database URL (SQLite fixture owns schema)."""
    import inventory.models  # noqa: F401 — register tables on SQLModel.metadata
    import telemetry.table  # noqa: F401 — same engine; include telemetry_events
    import rfp.models  # noqa: F401 — same engine; RFP tickets / metadata / sections

    if _is_test_environment() and not os.getenv("SUPABASE_DATABASE_URL", "").strip():
        return

    SQLModel.metadata.create_all(get_engine())


def assert_destructive_reset_allowed() -> None:
    """Block accidental drop_all against a shared Postgres database."""
    url = get_database_url()
    if url.startswith("sqlite"):
        return
    flag = os.getenv("INVENTORY_ALLOW_RESET", "").strip().lower()
    if flag in {"1", "true", "yes"}:
        return
    raise RuntimeError(
        "--reset is blocked against Postgres. Re-run with INVENTORY_ALLOW_RESET=1 "
        "if you intend to drop inventory tables."
    )
