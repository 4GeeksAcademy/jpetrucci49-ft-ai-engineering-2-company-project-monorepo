"""Create, update, and query job_runs. Lock = status='processing' only."""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (str(_REPO_ROOT), str(_API_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

JOB_NAME = "nightly_export"
JOB_RUNS_TABLE = "job_runs"


def _redact(message: str) -> str:
    try:
        from inventory.database import redact_secrets

        return redact_secrets(message)
    except Exception:
        return message


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def qualified_job_runs(engine: Engine) -> str:
    if engine.dialect.name == "postgresql":
        return "reporting.job_runs"
    return JOB_RUNS_TABLE


def get_jobs_engine() -> Engine:
    """Same engine as inventory / reporting.pipeline_runs."""
    from data.pipelines.monthly_clinic_supply_performance.db import get_pipeline_engine

    return get_pipeline_engine()


def ensure_job_runs_schema(engine: Engine | None = None) -> Engine:
    """Idempotent DDL for job_runs. Does not touch pipeline_runs."""
    engine = engine or get_jobs_engine()
    table = qualified_job_runs(engine)
    if engine.dialect.name == "postgresql":
        id_type = "uuid"
        ts_type = "timestamptz"
        statements = ["CREATE SCHEMA IF NOT EXISTS reporting"]
    else:
        id_type = "text"
        ts_type = "text"
        statements = []
    statements.extend(
        [
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
              id {id_type} PRIMARY KEY,
              job_name text NOT NULL,
              target_date date NOT NULL,
              status text NOT NULL,
              started_at {ts_type},
              finished_at {ts_type},
              error_message text,
              created_at {ts_type} NOT NULL
            )
            """,
            f"""
            CREATE INDEX IF NOT EXISTS ix_job_runs_job_name_target_date
            ON {table} (job_name, target_date)
            """,
        ]
    )
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    return engine


def has_processing_lock(job_name: str, engine: Engine | None = None) -> bool:
    """True if any row for job_name is processing (any target_date)."""
    engine = ensure_job_runs_schema(engine)
    table = qualified_job_runs(engine)
    with engine.connect() as conn:
        count = conn.execute(
            text(
                f"""
                SELECT COUNT(*) FROM {table}
                WHERE job_name = :job_name AND status = 'processing'
                """
            ),
            {"job_name": job_name},
        ).scalar()
    return int(count or 0) > 0


def has_completed_for_date(
    job_name: str,
    target_date: date,
    engine: Engine | None = None,
) -> bool:
    engine = ensure_job_runs_schema(engine)
    table = qualified_job_runs(engine)
    with engine.connect() as conn:
        count = conn.execute(
            text(
                f"""
                SELECT COUNT(*) FROM {table}
                WHERE job_name = :job_name
                  AND target_date = :target_date
                  AND status = 'completed'
                """
            ),
            {"job_name": job_name, "target_date": target_date.isoformat()},
        ).scalar()
    return int(count or 0) > 0


def claim_processing_lock(
    job_name: str,
    target_date: date,
    engine: Engine | None = None,
) -> str | None:
    """Insert pending, then processing, only if no other processing row exists.

    The lock is still `status='processing'` — not a second table or flag.
    Returns run_id, or None if another instance already holds the lock
    (caller must abort silently; the pending row is deleted).
    """
    engine = ensure_job_runs_schema(engine)
    table = qualified_job_runs(engine)
    run_id = str(uuid4())
    created = _iso(datetime.now(timezone.utc))
    started = created
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {table} (
                  id, job_name, target_date, status, started_at, finished_at,
                  error_message, created_at
                ) VALUES (
                  :id, :job_name, :target_date, 'pending', NULL, NULL, NULL, :created_at
                )
                """
            ),
            {
                "id": run_id,
                "job_name": job_name,
                "target_date": target_date.isoformat(),
                "created_at": created,
            },
        )
        held = conn.execute(
            text(
                f"""
                SELECT COUNT(*) FROM {table}
                WHERE job_name = :job_name AND status = 'processing' AND id != :id
                """
            ),
            {"job_name": job_name, "id": run_id},
        ).scalar()
        if int(held or 0) > 0:
            conn.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": run_id})
            return None
        conn.execute(
            text(
                f"""
                UPDATE {table}
                SET status = 'processing', started_at = :started_at
                WHERE id = :id
                """
            ),
            {"id": run_id, "started_at": started},
        )
    return run_id


def create_run(job_name: str, target_date: date, engine: Engine | None = None) -> str:
    engine = ensure_job_runs_schema(engine)
    table = qualified_job_runs(engine)
    run_id = str(uuid4())
    created = _iso(datetime.now(timezone.utc))
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {table} (
                  id, job_name, target_date, status, started_at, finished_at,
                  error_message, created_at
                ) VALUES (
                  :id, :job_name, :target_date, 'pending', NULL, NULL, NULL, :created_at
                )
                """
            ),
            {
                "id": run_id,
                "job_name": job_name,
                "target_date": target_date.isoformat(),
                "created_at": created,
            },
        )
    return run_id


def mark_processing(run_id: str, engine: Engine | None = None) -> None:
    engine = ensure_job_runs_schema(engine)
    table = qualified_job_runs(engine)
    started = _iso(datetime.now(timezone.utc))
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                UPDATE {table}
                SET status = 'processing', started_at = :started_at
                WHERE id = :id
                """
            ),
            {"id": run_id, "started_at": started},
        )


def mark_completed(run_id: str, engine: Engine | None = None) -> None:
    engine = ensure_job_runs_schema(engine)
    table = qualified_job_runs(engine)
    finished = _iso(datetime.now(timezone.utc))
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                UPDATE {table}
                SET status = 'completed', finished_at = :finished_at, error_message = NULL
                WHERE id = :id
                """
            ),
            {"id": run_id, "finished_at": finished},
        )


def mark_failed(run_id: str, error_message: str, engine: Engine | None = None) -> None:
    engine = ensure_job_runs_schema(engine)
    table = qualified_job_runs(engine)
    finished = _iso(datetime.now(timezone.utc))
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                UPDATE {table}
                SET status = 'failed',
                    finished_at = :finished_at,
                    error_message = :error_message
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": finished,
                "error_message": _redact(error_message),
            },
        )


def get_run(run_id: str, engine: Engine | None = None) -> dict | None:
    engine = ensure_job_runs_schema(engine)
    table = qualified_job_runs(engine)
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT * FROM {table} WHERE id = :id"),
            {"id": run_id},
        ).mappings().first()
    return dict(row) if row else None
