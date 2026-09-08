"""Isolated transform tests for Monthly Clinic Supply Performance KPIs.

No database, HTTP, or Prefect server. Event shape matches CONTEXT telemetry.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from data.process.clinic_month_kpis import compute_clinic_month_kpis
from data.process.inbound_cost import inbound_event_cost

AUGUST = date(2026, 8, 1)


def _event(
    event_type: str,
    *,
    event_id: str,
    clinic_id: int = 2,
    country: str = "US",
    timestamp: str = "2026-08-10T12:00:00+00:00",
    value: float | None = None,
    **tag_extras: Any,
) -> dict[str, Any]:
    tags: dict[str, Any] = {
        "clinic_id": clinic_id,
        "country": country,
        "eventId": event_id,
        **tag_extras,
    }
    return {
        "timestamp": timestamp,
        "event_type": event_type,
        "value": value,
        "tags": tags,
    }


def test_inbound_event_cost_prefers_total_cost() -> None:
    cost, missing = inbound_event_cost(
        {"total_cost": 24, "unit_cost": 9, "quantity": 8}
    )
    assert float(cost) == 24
    assert missing is False


def test_supply_cost_per_clinic_hand_calculated() -> None:
    events = [
        _event(
            "inbound_order_created",
            event_id="A",
            quantity=10,
            unit_cost=12.5,
            value=10,
        ),
        _event(
            "inbound_order_created",
            event_id="A",
            timestamp="2026-08-10T12:01:00+00:00",
            quantity=10,
            unit_cost=12.5,
            value=10,
        ),
        _event(
            "inbound_order_created",
            event_id="B",
            timestamp="2026-08-12T09:00:00+00:00",
            quantity=4,
            unit_cost=20,
            value=4,
        ),
        _event("outbound_order_created", event_id="C"),
        _event(
            "outbound_order_created",
            event_id="D",
            timestamp="2026-08-15T11:00:00+00:00",
        ),
        _event("stock_threshold_triggered", event_id="E"),
        _event("supply_expiry_flagged", event_id="F"),
        _event(
            "inbound_order_created",
            event_id="UK-1",
            clinic_id=10,
            country="UK",
            timestamp="2026-08-06T10:00:00+00:00",
            total_cost=24,
            quantity=8,
        ),
    ]
    rows, missing = compute_clinic_month_kpis(events, AUGUST)
    by_clinic = {row["clinic_id"]: row for row in rows}

    assert by_clinic["austin-north"]["total_supply_cost"] == 205.0
    assert by_clinic["austin-north"]["supply_consumption_count"] == 2
    assert by_clinic["austin-north"]["critical_stockout_count"] == 1
    assert by_clinic["austin-north"]["expiry_risk_count"] == 1
    assert by_clinic["austin-north"]["currency"] == "USD"
    assert by_clinic["austin-north"]["clinic_id"] == "austin-north"

    assert by_clinic["london-city"]["total_supply_cost"] == 24.0
    assert by_clinic["london-city"]["currency"] == "GBP"
    costs = [row["total_supply_cost"] for row in rows]
    assert 205.0 + 24.0 not in costs
    assert missing == 0


def test_supply_consumption_volume_counts_outbound_only() -> None:
    events = [
        _event(
            "inbound_order_created",
            event_id="in-1",
            quantity=3,
            unit_cost=1,
        ),
        _event("outbound_order_created", event_id="out-1"),
        _event("outbound_order_created", event_id="out-2"),
        _event("stock_threshold_triggered", event_id="th-1"),
    ]
    rows, _ = compute_clinic_month_kpis(events, AUGUST)
    assert rows[0]["supply_consumption_count"] == 2
    assert rows[0]["total_supply_cost"] == 3.0


def test_critical_stockout_frequency_counts_threshold_events() -> None:
    events = [
        _event("stock_threshold_triggered", event_id="s1"),
        _event("stock_threshold_triggered", event_id="s2"),
        _event("outbound_order_created", event_id="o1"),
    ]
    rows, _ = compute_clinic_month_kpis(events, AUGUST)
    assert rows[0]["critical_stockout_count"] == 2
    assert rows[0]["supply_consumption_count"] == 1


def test_expiry_risk_count_counts_flagged_batches() -> None:
    events = [
        _event("supply_expiry_flagged", event_id="x1"),
        _event("supply_expiry_flagged", event_id="x2"),
        _event("supply_expiry_flagged", event_id="x3"),
        _event("inbound_order_created", event_id="in-1", quantity=1, unit_cost=2),
    ]
    rows, _ = compute_clinic_month_kpis(events, AUGUST)
    assert rows[0]["expiry_risk_count"] == 3


def test_transform_drops_unknown_clinic_and_country_mismatch() -> None:
    events = [
        _event("outbound_order_created", event_id="ok"),
        _event("outbound_order_created", event_id="unknown", clinic_id=99),
        _event("outbound_order_created", event_id="mismatch", country="UK"),
        _event(
            "outbound_order_created",
            event_id="no-clinic",
            clinic_id=None,  # type: ignore[arg-type]
        ),
        {
            "timestamp": "not-a-date",
            "event_type": "outbound_order_created",
            "tags": {"clinic_id": 2, "country": "US", "eventId": "bad-ts"},
        },
        {
            "timestamp": "2026-08-10T12:00:00+00:00",
            "event_type": "outbound_order_created",
            "tags": "not-a-dict",
        },
        _event(
            "inbound_order_created",
            event_id="no-cost",
            quantity=5,
        ),
    ]
    rows, missing = compute_clinic_month_kpis(events, AUGUST)
    by_clinic = {row["clinic_id"]: row for row in rows}
    assert set(by_clinic) == {"austin-north"}
    assert by_clinic["austin-north"]["supply_consumption_count"] == 1
    assert by_clinic["austin-north"]["total_supply_cost"] == 0.0
    assert missing == 1
