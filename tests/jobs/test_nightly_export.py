"""Nightly script control flow — no FastAPI, no live Prefect."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from jobs.job_runner import (
    JOB_NAME,
    claim_processing_lock,
    create_run,
    ensure_job_runs_schema,
    get_run,
    has_processing_lock,
    mark_processing,
)
from scripts.nightly_export import (
    csv_path_for,
    export_csv_if_missing,
    main,
    month_start_for,
    pipeline_command,
)


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'export.db'}")
    ensure_job_runs_schema(eng)
    return eng


def test_month_start_for_target_date() -> None:
    assert month_start_for(date(2026, 9, 7)) == date(2026, 9, 1)


def test_pipeline_command_uses_repo_cli_and_no_sample() -> None:
    command = pipeline_command(date(2026, 9, 7))
    assert command[1].endswith("data/pipelines/pipeline.py")
    assert "--month-start" in command
    assert "2026-09-01" in command
    assert "--no-sample" in command
    assert "telemetry_kpi_daily" not in " ".join(command)


def test_export_skips_existing_file(tmp_path: Path, engine) -> None:
    target = date(2026, 9, 7)
    path = csv_path_for(target, tmp_path)
    path.write_text("already-here\n", encoding="utf-8")
    export_csv_if_missing(target, raw_dir=tmp_path, engine=engine)
    assert path.read_text(encoding="utf-8") == "already-here\n"


def test_export_writes_header_when_no_telemetry_table_is_missing(
    tmp_path: Path, engine
) -> None:
    with pytest.raises(RuntimeError, match="telemetry_events"):
        export_csv_if_missing(date(2026, 9, 7), raw_dir=tmp_path, engine=engine)


def test_export_writes_header_only_for_empty_day(tmp_path: Path, engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE telemetry_events (
                  id text PRIMARY KEY,
                  timestamp text NOT NULL,
                  service text NOT NULL,
                  event_type text NOT NULL,
                  level text NOT NULL,
                  value text,
                  message text,
                  tags text
                )
                """
            )
        )
    path = export_csv_if_missing(date(2026, 9, 7), raw_dir=tmp_path, engine=engine)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines == [
        "id,timestamp,service,event_type,level,value,message,tags"
    ]


def test_export_writes_telemetry_rows_for_target_date(tmp_path: Path, engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE telemetry_events (
                  id text PRIMARY KEY,
                  timestamp text NOT NULL,
                  service text NOT NULL,
                  event_type text NOT NULL,
                  level text NOT NULL,
                  value text,
                  message text,
                  tags text
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO telemetry_events
                  (id, timestamp, service, event_type, level, value, message, tags)
                VALUES
                  ('e1', '2026-09-07 12:00:00', 'backoffice', 'outbound_order_created',
                   'info', '2', NULL, '{"clinic_id": 2}'),
                  ('e2', '2026-09-08 00:00:00', 'backoffice', 'outbound_order_created',
                   'info', '9', NULL, '{}')
                """
            )
        )
    path = export_csv_if_missing(date(2026, 9, 7), raw_dir=tmp_path, engine=engine)
    body = path.read_text(encoding="utf-8")
    assert path.name == "telemetry_2026-09-07.csv"
    assert "outbound_order_created" in body
    assert "e1" in body
    assert "e2" not in body


def test_main_aborts_silently_when_processing(
    monkeypatch: pytest.MonkeyPatch, engine
) -> None:
    run_id = create_run(JOB_NAME, date(2026, 9, 7), engine)
    mark_processing(run_id, engine)

    monkeypatch.setattr("scripts.nightly_export.ensure_job_runs_schema", lambda: engine)
    monkeypatch.setattr(
        "scripts.nightly_export.has_processing_lock",
        lambda name: has_processing_lock(name, engine),
    )
    monkeypatch.setattr(
        "scripts.nightly_export.resolve_target_date", lambda: date(2026, 9, 7)
    )
    called = {"pipeline": False}

    def _fail_pipeline(_target):
        called["pipeline"] = True

    monkeypatch.setattr("scripts.nightly_export.run_pipeline_subprocess", _fail_pipeline)
    assert main() == 0
    assert called["pipeline"] is False


def test_main_skips_completed_duplicate(
    monkeypatch: pytest.MonkeyPatch, engine
) -> None:
    from jobs.job_runner import mark_completed

    run_id = create_run(JOB_NAME, date(2026, 9, 7), engine)
    mark_processing(run_id, engine)
    mark_completed(run_id, engine)

    monkeypatch.setattr("scripts.nightly_export.ensure_job_runs_schema", lambda: engine)
    monkeypatch.setattr(
        "scripts.nightly_export.has_processing_lock",
        lambda name: has_processing_lock(name, engine),
    )
    monkeypatch.setattr(
        "scripts.nightly_export.has_completed_for_date",
        lambda name, day: name == JOB_NAME and day == date(2026, 9, 7),
    )
    monkeypatch.setattr(
        "scripts.nightly_export.resolve_target_date", lambda: date(2026, 9, 7)
    )
    called = {"pipeline": False, "export": False}
    monkeypatch.setattr(
        "scripts.nightly_export.export_csv_if_missing",
        lambda *_a, **_k: called.__setitem__("export", True),
    )
    monkeypatch.setattr(
        "scripts.nightly_export.run_pipeline_subprocess",
        lambda *_a, **_k: called.__setitem__("pipeline", True),
    )
    assert main() == 0
    assert called["pipeline"] is False
    assert called["export"] is False


def test_main_marks_failed_when_pipeline_raises(
    monkeypatch: pytest.MonkeyPatch, engine
) -> None:
    monkeypatch.setattr("scripts.nightly_export.ensure_job_runs_schema", lambda: engine)
    monkeypatch.setattr(
        "scripts.nightly_export.has_processing_lock",
        lambda name: has_processing_lock(name, engine),
    )
    monkeypatch.setattr(
        "scripts.nightly_export.has_completed_for_date",
        lambda name, day: False,
    )
    monkeypatch.setattr(
        "scripts.nightly_export.claim_processing_lock",
        lambda name, day: claim_processing_lock(name, day, engine),
    )
    monkeypatch.setattr(
        "scripts.nightly_export.get_run",
        lambda run_id: get_run(run_id, engine),
    )
    failed_ids: list[str] = []

    def _mark_failed(run_id: str, message: str) -> None:
        from jobs.job_runner import mark_failed as real_fail

        failed_ids.append(run_id)
        real_fail(run_id, message, engine)

    monkeypatch.setattr("scripts.nightly_export.mark_failed", _mark_failed)
    monkeypatch.setattr(
        "scripts.nightly_export.mark_completed", lambda run_id: None
    )
    monkeypatch.setattr(
        "scripts.nightly_export.resolve_target_date", lambda: date(2026, 9, 7)
    )
    monkeypatch.setattr(
        "scripts.nightly_export.export_csv_if_missing", lambda *_a, **_k: None
    )

    def _boom(_target):
        raise RuntimeError("pipeline exited 1")

    monkeypatch.setattr("scripts.nightly_export.run_pipeline_subprocess", _boom)

    assert main() == 1
    assert failed_ids
    assert has_processing_lock(JOB_NAME, engine) is False
    row = get_run(failed_ids[0], engine)
    assert row is not None
    assert row["status"] == "failed"
    assert "pipeline exited 1" in (row["error_message"] or "")
