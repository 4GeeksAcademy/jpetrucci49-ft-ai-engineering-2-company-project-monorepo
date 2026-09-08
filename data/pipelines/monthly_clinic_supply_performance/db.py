"""Engine + reporting schema. Reads telemetry_events; never writes it."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine

from data.pipelines.paths import LOCAL_REPORTING_DB, ensure_import_paths

ensure_import_paths()

PIPELINE_NAME = "monthly_clinic_supply_performance"
KPI_TABLE = "monthly_clinic_supply_performance"
RUNS_TABLE = "pipeline_runs"


def _redact(message: str) -> str:
    try:
        from inventory.database import redact_secrets

        return redact_secrets(message)
    except Exception:
        return message


def qualified_table(engine: Engine, name: str) -> str:
    if engine.dialect.name == "postgresql":
        return f"reporting.{name}"
    return name


def get_pipeline_engine() -> Engine:
    """Reuse the inventory/API engine when configured; otherwise local SQLite."""
    from inventory.database import (
        _engine,
        configure_engine,
        get_database_url,
        get_engine,
        load_local_env,
        reset_engine,
    )

    if _engine is not None:
        return get_engine()

    try:
        load_local_env()
        if os.getenv("SUPABASE_DATABASE_URL", "").strip():
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
    except Exception:
        reset_engine()

    LOCAL_REPORTING_DB.parent.mkdir(parents=True, exist_ok=True)
    return configure_engine(f"sqlite:///{LOCAL_REPORTING_DB}")


def ensure_reporting_schema(engine: Engine | None = None) -> Engine:
    engine = engine or get_pipeline_engine()
    kpi = qualified_table(engine, KPI_TABLE)
    runs = qualified_table(engine, RUNS_TABLE)
    statements: list[str] = []
    if engine.dialect.name == "postgresql":
        statements.append("CREATE SCHEMA IF NOT EXISTS reporting")
        id_type = "uuid"
        ts_type = "timestamptz"
    else:
        id_type = "text"
        ts_type = "text"

    statements.extend(
        [
            f"""
            CREATE TABLE IF NOT EXISTS {kpi} (
              id {id_type} PRIMARY KEY,
              clinic_id text NOT NULL,
              country text NOT NULL,
              month_start date NOT NULL,
              total_supply_cost numeric NOT NULL DEFAULT 0,
              supply_consumption_count integer NOT NULL DEFAULT 0,
              critical_stockout_count integer NOT NULL DEFAULT 0,
              expiry_risk_count integer NOT NULL DEFAULT 0,
              currency text NOT NULL,
              computed_at {ts_type} NOT NULL,
              UNIQUE (clinic_id, month_start)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {runs} (
              id {id_type} PRIMARY KEY,
              pipeline_name text NOT NULL,
              month_start date NOT NULL,
              started_at {ts_type} NOT NULL,
              finished_at {ts_type},
              status text NOT NULL,
              records_read integer NOT NULL DEFAULT 0,
              records_written integer NOT NULL DEFAULT 0,
              error_message text,
              prefect_flow_run_id text
            )
            """,
        ]
    )
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    return engine


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def fail_stale_running(engine: Engine) -> None:
    runs = qualified_table(engine, RUNS_TABLE)
    now = _iso(datetime.now(timezone.utc))
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                UPDATE {runs}
                SET status = 'failed',
                    finished_at = :finished_at,
                    error_message = 'stale running row closed by a later start'
                WHERE pipeline_name = :pipeline_name AND status = 'running'
                """
            ),
            {"finished_at": now, "pipeline_name": PIPELINE_NAME},
        )


def begin_pipeline_run(
    month_start: date,
    prefect_flow_run_id: str | None = None,
) -> str:
    # Overlap lock: a second start (manual POST while cron is still Running)
    # closes leftover `running` rows so Okonkwo does not read a stale pack.
    # Answers PIPELINE_DESIGN.md §6 / “what if two runs overlap?”
    engine = ensure_reporting_schema()
    fail_stale_running(engine)
    run_id = str(uuid4())
    runs = qualified_table(engine, RUNS_TABLE)
    started = _iso(datetime.now(timezone.utc))
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {runs} (
                  id, pipeline_name, month_start, started_at, finished_at, status,
                  records_read, records_written, error_message, prefect_flow_run_id
                ) VALUES (
                  :id, :pipeline_name, :month_start, :started_at, NULL, 'running',
                  0, 0, NULL, :prefect_flow_run_id
                )
                """
            ),
            {
                "id": run_id,
                "pipeline_name": PIPELINE_NAME,
                "month_start": month_start.isoformat(),
                "started_at": started,
                "prefect_flow_run_id": prefect_flow_run_id,
            },
        )
    return run_id


def complete_pipeline_run(
    run_id: str,
    status: str,
    *,
    records_read: int = 0,
    records_written: int = 0,
    error_message: str | None = None,
) -> dict[str, Any]:
    engine = ensure_reporting_schema()
    runs = qualified_table(engine, RUNS_TABLE)
    finished = _iso(datetime.now(timezone.utc))
    safe_error = _redact(error_message) if error_message else None
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                UPDATE {runs}
                SET finished_at = :finished_at,
                    status = :status,
                    records_read = :records_read,
                    records_written = :records_written,
                    error_message = :error_message
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": finished,
                "status": status,
                "records_read": records_read,
                "records_written": records_written,
                "error_message": safe_error,
            },
        )
        row = conn.execute(
            text(f"SELECT * FROM {runs} WHERE id = :id"),
            {"id": run_id},
        ).mappings().first()
    return dict(row) if row else {
        "id": run_id,
        "status": status,
        "records_read": records_read,
        "records_written": records_written,
        "error_message": safe_error,
        "finished_at": finished,
    }
