"""Subflow: extract Monthly Clinic Supply events for one UTC month."""

from __future__ import annotations

from datetime import date
from typing import Any

from prefect import flow, get_run_logger

from data.pipelines.monthly_clinic_supply_performance.extract import (
    extract_from_sample,
    extract_month,
)


@flow(name="extract_monthly_clinic_supply_events")
def extract_monthly_clinic_supply_events(
    month_start: date,
    allow_sample: bool,
) -> dict[str, Any]:
    """Return extract_path, records_read, content_hash, source."""
    run_logger = get_run_logger()
    extract_state = extract_month(month_start, return_state=True)
    if extract_state.is_completed():
        return extract_state.result()
    if allow_sample:
        run_logger.warning(
            "extract_month failed; using data/raw/telemetry_events_sample.json"
        )
        return extract_from_sample(month_start)
    raise RuntimeError(
        f"extract_month failed: {extract_state.message or extract_state.type}"
    )
