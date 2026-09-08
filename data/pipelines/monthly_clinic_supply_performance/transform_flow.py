"""Subflow: compute Monthly Clinic Supply KPIs from an extract file."""

from __future__ import annotations

from datetime import date
from typing import Any

from prefect import flow

from data.pipelines.monthly_clinic_supply_performance.transform import (
    transform_clinic_month,
    write_eval_snapshot,
)


@flow(name="transform_monthly_clinic_supply_kpis")
def transform_monthly_clinic_supply_kpis(
    extract_path: str,
    month_start: date,
    content_hash: str,
) -> dict[str, Any]:
    """Return kpis, missing_inbound_cost_count, kpis_path."""
    return transform_clinic_month(extract_path, month_start, content_hash)


@flow(name="snapshot_monthly_clinic_supply_eval")
def snapshot_monthly_clinic_supply_eval(
    kpis: list[dict[str, Any]],
    month_start: date,
) -> str:
    """Optional eval snapshot under data/eval/ — non-critical."""
    return write_eval_snapshot(kpis, month_start)
