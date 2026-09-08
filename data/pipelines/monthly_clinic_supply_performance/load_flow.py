"""Subflow: upsert Monthly Clinic Supply Performance destination rows."""

from __future__ import annotations

from datetime import date
from typing import Any

from prefect import flow

from data.pipelines.monthly_clinic_supply_performance.load import load_clinic_month


@flow(name="load_monthly_clinic_supply_performance")
def load_monthly_clinic_supply_performance(
    kpis: list[dict[str, Any]],
    month_start: date,
) -> int:
    """Upsert reporting.monthly_clinic_supply_performance; return records_written."""
    return load_clinic_month(kpis, month_start)
