#!/usr/bin/env python3
"""Nightly telemetry CSV backup + Milestone 6 pipeline subprocess.

Independent of FastAPI. Lock = job_runs.status='processing'.
Usage:
  python scripts/nightly_export.py
  TARGET_DATE=2026-09-07 python scripts/nightly_export.py
"""

from __future__ import annotations

import csv
import json
import logging
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_API_ROOT = _REPO_ROOT / "services" / "api"
_SERVICES_ROOT = _REPO_ROOT / "services"
for _path in (str(_REPO_ROOT), str(_API_ROOT), str(_SERVICES_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from jobs.job_runner import (  # noqa: E402
    JOB_NAME,
    create_run,
    ensure_job_runs_schema,
    get_jobs_engine,
    has_completed_for_date,
    has_processing_lock,
    mark_completed,
    mark_failed,
    mark_processing,
)
from data.pipelines.paths import RAW_DIR  # noqa: E402

CSV_COLUMNS = (
    "id",
    "timestamp",
    "service",
    "event_type",
    "level",
    "value",
    "message",
    "tags",
)

logger = logging.getLogger("nightly_export")


class _JobLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "job_name"):
            record.job_name = JOB_NAME
        if not hasattr(record, "status"):
            record.status = "-"
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_JobLogFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s job=%(job_name)s status=%(status)s %(message)s")
    )
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_event(level: int, status: str, message: str) -> None:
    logger.log(level, message, extra={"job_name": JOB_NAME, "status": status})


def resolve_target_date(raw: str | None = None) -> date:
    """TARGET_DATE=YYYY-MM-DD or yesterday UTC."""
    value = raw if raw is not None else os.getenv("TARGET_DATE", "").strip()
    if not value:
        return datetime.now(timezone.utc).date() - timedelta(days=1)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"TARGET_DATE must be YYYY-MM-DD, got {value!r}") from exc


def month_start_for(target_date: date) -> date:
    return target_date.replace(day=1)


def csv_path_for(target_date: date, raw_dir: Path | None = None) -> Path:
    directory = raw_dir or RAW_DIR
    return directory / f"telemetry_{target_date.isoformat()}.csv"


def pipeline_command(target_date: date) -> list[str]:
    month = month_start_for(target_date)
    return [
        sys.executable,
        str(_REPO_ROOT / "data" / "pipelines" / "pipeline.py"),
        "--month-start",
        month.isoformat(),
        "--no-sample",
    ]


def _window_bounds(target_date: date) -> tuple[datetime, datetime]:
    start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _bind_timestamp(engine: Any, value: datetime) -> Any:
    if engine.dialect.name == "sqlite":
        return value.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
    return value


def _tags_cell(tags: Any) -> str:
    if tags is None:
        return "{}"
    if isinstance(tags, str):
        return tags
    return json.dumps(tags, default=str)


def export_csv_if_missing(
    target_date: date,
    *,
    raw_dir: Path | None = None,
    engine: Any | None = None,
) -> Path:
    """Write data/raw/telemetry_YYYY-MM-DD.csv if absent. Read-only on telemetry_events."""
    from sqlalchemy import inspect, text

    path = csv_path_for(target_date, raw_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        log_event(logging.INFO, "processing", f"export already present {path.name}")
        return path

    engine = engine or get_jobs_engine()
    inspector = inspect(engine)
    names = set(inspector.get_table_names())
    if engine.dialect.name == "postgresql":
        names.update(inspector.get_table_names(schema="public"))
    if "telemetry_events" not in names:
        raise RuntimeError("telemetry_events table is not available")

    start, end = _window_bounds(target_date)
    sql = text(
        """
        SELECT id, timestamp, service, event_type, level, value, message, tags
        FROM telemetry_events
        WHERE timestamp >= :start AND timestamp < :end
        ORDER BY timestamp, id
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "start": _bind_timestamp(engine, start),
                "end": _bind_timestamp(engine, end),
            },
        ).mappings()
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "id": str(row["id"]),
                        "timestamp": (
                            row["timestamp"].isoformat()
                            if hasattr(row["timestamp"], "isoformat")
                            else str(row["timestamp"])
                        ),
                        "service": row["service"],
                        "event_type": row["event_type"],
                        "level": row["level"],
                        "value": "" if row["value"] is None else str(row["value"]),
                        "message": "" if row["message"] is None else row["message"],
                        "tags": _tags_cell(row["tags"]),
                    }
                )
    log_event(logging.INFO, "processing", f"wrote export {path.name}")
    return path


def run_pipeline_subprocess(target_date: date) -> None:
    command = pipeline_command(target_date)
    log_event(
        logging.INFO,
        "processing",
        f"trigger pipeline {' '.join(command[1:])}",
    )
    subprocess.run(command, check=True, cwd=_REPO_ROOT)


def main(argv: list[str] | None = None) -> int:
    del argv  # env-driven; reserved for CLI compatibility
    configure_logging()
    try:
        target_date = resolve_target_date()
    except ValueError as exc:
        log_event(logging.ERROR, "failed", str(exc))
        return 1

    ensure_job_runs_schema()

    if has_processing_lock(JOB_NAME):
        log_event(
            logging.INFO,
            "cancelled",
            f"aborted silently; {JOB_NAME} already processing",
        )
        return 0

    if has_completed_for_date(JOB_NAME, target_date):
        log_event(
            logging.INFO,
            "skipped",
            f"duplicate completed run for {target_date.isoformat()}",
        )
        return 0

    run_id = create_run(JOB_NAME, target_date)
    mark_processing(run_id)
    log_event(logging.INFO, "processing", f"start target_date={target_date.isoformat()}")
    try:
        export_csv_if_missing(target_date)
        run_pipeline_subprocess(target_date)
        mark_completed(run_id)
        log_event(logging.INFO, "completed", f"finish target_date={target_date.isoformat()}")
        return 0
    except Exception as exc:
        from inventory.database import redact_secrets

        message = redact_secrets(str(exc))
        mark_failed(run_id, message)
        log_event(logging.ERROR, "failed", message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
