"""Prefect flow monthly_clinic_supply_performance — orchestrates named subflows."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from data.pipelines.paths import ensure_import_paths, last_run_log_path

ensure_import_paths()

from prefect import flow, get_run_logger

from data.pipelines.monthly_clinic_supply_performance.db import (
    PIPELINE_NAME,
    begin_pipeline_run,
    complete_pipeline_run,
)
from data.pipelines.monthly_clinic_supply_performance.extract_flow import (
    extract_monthly_clinic_supply_events,
)
from data.pipelines.monthly_clinic_supply_performance.load_flow import (
    load_monthly_clinic_supply_performance,
)
from data.pipelines.monthly_clinic_supply_performance.transform_flow import (
    snapshot_monthly_clinic_supply_eval,
    transform_monthly_clinic_supply_kpis,
)

logger = logging.getLogger(__name__)


def resolve_month_start(value: date | str | None) -> date:
    if value is None:
        today = datetime.now(timezone.utc).date()
        first_this_month = today.replace(day=1)
        previous = first_this_month - timedelta(days=1)
        return previous.replace(day=1)
    if isinstance(value, str):
        value = date.fromisoformat(value)
    return value.replace(day=1)


def _prefect_run_id() -> str | None:
    try:
        from prefect.runtime import flow_run

        return str(flow_run.id) if flow_run.id else None
    except Exception:
        return None


def _write_run_log(metadata: dict[str, Any]) -> None:
    path = last_run_log_path()
    path.write_text(json.dumps(metadata, default=str, indent=2), encoding="utf-8")


@flow(name="monthly_clinic_supply_performance")
def run_monthly_clinic_supply_performance(
    month_start: date | str | None = None,
    allow_sample: bool = False,
) -> dict[str, Any]:
    """Orchestrate extract → transform → eval snapshot → load for one UTC month."""
    run_logger = get_run_logger()
    month = resolve_month_start(month_start)
    run_id = begin_pipeline_run(month, prefect_flow_run_id=_prefect_run_id())
    records_read = 0
    records_written = 0
    try:
        extracted = extract_monthly_clinic_supply_events(month, allow_sample)
        records_read = int(extracted["records_read"])

        transformed = transform_monthly_clinic_supply_kpis(
            extracted["extract_path"],
            month,
            extracted["content_hash"],
        )
        kpis = transformed["kpis"]

        # Optional / non-critical: a failed eval snapshot must not interrupt ETL.
        eval_state = snapshot_monthly_clinic_supply_eval(
            kpis, month, return_state=True
        )
        if eval_state.is_failed():
            run_logger.warning(
                "snapshot_monthly_clinic_supply_eval failed; continuing load"
            )

        records_written = load_monthly_clinic_supply_performance(kpis, month)
        metadata = complete_pipeline_run(
            run_id,
            "completed",
            records_read=records_read,
            records_written=records_written,
        )
        _write_run_log(metadata)
        result = {
            "pipeline_name": PIPELINE_NAME,
            "month_start": month.isoformat(),
            "status": "completed",
            "records_read": records_read,
            "records_written": records_written,
            "source": extracted.get("source"),
            "missing_inbound_cost_count": transformed.get(
                "missing_inbound_cost_count", 0
            ),
        }
        run_logger.info("completed month_start=%s written=%s", month, records_written)
        return result
    except Exception as exc:
        complete_pipeline_run(
            run_id,
            "failed",
            records_read=records_read,
            records_written=records_written,
            error_message=str(exc),
        )
        _write_run_log(
            {
                "id": run_id,
                "status": "failed",
                "month_start": month.isoformat(),
                "error_message": str(exc),
                "records_read": records_read,
                "records_written": records_written,
            }
        )
        raise
