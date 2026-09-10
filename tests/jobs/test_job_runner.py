"""job_runs lock, idempotency, and failed-status tests. SQLite only."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text

from jobs.job_runner import (
    JOB_NAME,
    claim_processing_lock,
    create_run,
    ensure_job_runs_schema,
    get_run,
    has_completed_for_date,
    has_processing_lock,
    mark_completed,
    mark_failed,
    mark_processing,
)
from scripts.nightly_export import resolve_target_date
from scripts.nightly_loop import seconds_until_next_0205_utc


@pytest.fixture
def engine(tmp_path):
    db = tmp_path / "job_runs.db"
    eng = create_engine(f"sqlite:///{db}")
    ensure_job_runs_schema(eng)
    return eng


def test_has_processing_lock_is_the_only_lock(engine) -> None:
    target = date(2026, 9, 7)
    assert has_processing_lock(JOB_NAME, engine) is False
    run_id = create_run(JOB_NAME, target, engine)
    assert has_processing_lock(JOB_NAME, engine) is False
    mark_processing(run_id, engine)
    assert has_processing_lock(JOB_NAME, engine) is True
    # Lock is by job_name, not target_date.
    assert has_processing_lock(JOB_NAME, engine) is True


def test_has_completed_for_date_ignores_failed(engine) -> None:
    target = date(2026, 9, 7)
    failed_id = create_run(JOB_NAME, target, engine)
    mark_processing(failed_id, engine)
    mark_failed(failed_id, "boom", engine)
    assert has_completed_for_date(JOB_NAME, target, engine) is False
    assert has_processing_lock(JOB_NAME, engine) is False

    done_id = create_run(JOB_NAME, target, engine)
    mark_processing(done_id, engine)
    mark_completed(done_id, engine)
    assert has_completed_for_date(JOB_NAME, target, engine) is True
    assert has_completed_for_date(JOB_NAME, date(2026, 9, 8), engine) is False


def test_failed_run_does_not_remain_processing(engine) -> None:
    run_id = create_run(JOB_NAME, date(2026, 9, 7), engine)
    mark_processing(run_id, engine)
    try:
        raise RuntimeError("export failed")
    except RuntimeError as exc:
        mark_failed(run_id, str(exc), engine)
    row = get_run(run_id, engine)
    assert row is not None
    assert row["status"] == "failed"
    assert "export failed" in (row["error_message"] or "")
    assert row["finished_at"]
    assert has_processing_lock(JOB_NAME, engine) is False


def test_pending_then_processing_then_completed(engine) -> None:
    run_id = create_run(JOB_NAME, date(2026, 9, 1), engine)
    assert get_run(run_id, engine)["status"] == "pending"
    mark_processing(run_id, engine)
    assert get_run(run_id, engine)["status"] == "processing"
    mark_completed(run_id, engine)
    assert get_run(run_id, engine)["status"] == "completed"


def test_resolve_target_date_yesterday_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TARGET_DATE", raising=False)
    expected = datetime.now(timezone.utc).date() - timedelta(days=1)
    assert resolve_target_date() == expected


def test_resolve_target_date_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARGET_DATE", "2026-09-07")
    assert resolve_target_date() == date(2026, 9, 7)


def test_resolve_target_date_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARGET_DATE", "09-07-2026")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        resolve_target_date()


def test_seconds_until_next_0205_utc() -> None:
    before = datetime(2026, 9, 8, 1, 0, tzinfo=timezone.utc)
    assert seconds_until_next_0205_utc(before) == 65 * 60
    after = datetime(2026, 9, 8, 2, 5, tzinfo=timezone.utc)
    assert seconds_until_next_0205_utc(after) == 24 * 60 * 60


def test_schema_creates_index(engine) -> None:
    rows = engine.connect().execute(text("PRAGMA index_list('job_runs')")).fetchall()
    names = {row[1] for row in rows}
    assert "ix_job_runs_job_name_target_date" in names


def test_claim_processing_lock_rejects_second_instance(engine) -> None:
    target = date(2026, 9, 7)
    first = claim_processing_lock(JOB_NAME, target, engine)
    second = claim_processing_lock(JOB_NAME, target, engine)
    assert first is not None
    assert second is None
    assert get_run(first, engine)["status"] == "processing"
    assert has_processing_lock(JOB_NAME, engine) is True


def test_claim_processing_lock_concurrent_threads(tmp_path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    eng = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}",
        connect_args={"check_same_thread": False},
    )
    ensure_job_runs_schema(eng)
    target = date(2026, 9, 7)

    def claim() -> str | None:
        return claim_processing_lock(JOB_NAME, target, eng)

    with ThreadPoolExecutor(max_workers=2) as pool:
        won = list(pool.map(lambda _: claim(), range(2)))
    held = [run_id for run_id in won if run_id is not None]
    assert len(held) == 1
    assert won.count(None) == 1
    assert get_run(held[0], eng)["status"] == "processing"
