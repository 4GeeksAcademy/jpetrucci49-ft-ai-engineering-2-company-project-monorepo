"""Tests for incident analysis logic (API-042)."""

from __future__ import annotations

from pathlib import Path

import app.incidents.store as analysis_store
import pandas as pd
import pytest
from app.incidents.analysis import (
    INVALID_RULE_LABELS,
    analyze,
    load_incidents_from_bytes,
    metrics_to_csv_string,
    validate_columns,
    validate_record,
)
from app.incidents.store import get_last_analysis, save_analysis

REPO_ROOT = Path(__file__).resolve().parents[3]
INCIDENTS_CSV = REPO_ROOT / "scripts" / "incidents.csv"


@pytest.fixture(autouse=True)
def reset_analysis_store():
    analysis_store._last_result = None
    yield
    analysis_store._last_result = None


def test_in1_analyze_fixture_csv_matches_expected_totals():
    content = INCIDENTS_CSV.read_bytes()
    df = load_incidents_from_bytes(content)
    metrics = analyze(df)
    assert metrics["total"] == 100
    assert metrics["valid_count"] == 94
    assert metrics["invalid_count"] == 6


def test_in2_multiple_validation_rules_counted_per_rule():
    row = pd.Series(
        {
            "clinic_id": "INVALID",
            "country": "US",
            "category": "NOT_REAL",
            "description": "bad",
            "status": "OPEN",
            "patient_id": "bad-id",
            "satisfaction_score": "",
        }
    )
    violations = validate_record(row)
    assert "invalid_clinic_id" in violations
    assert "invalid_category" in violations
    assert "empty_description" in violations
    assert "missing_patient_id" in violations

    df = pd.DataFrame([row])
    metrics = analyze(df)
    assert metrics["invalid_counts"]["invalid_clinic_id"] == 1
    assert metrics["invalid_counts"]["invalid_category"] == 1


def test_in3_store_overwrites_previous_analysis():
    first = save_analysis("first.csv", {"total": 1}, "metric,value\n")
    second = save_analysis("second.csv", {"total": 2}, "metric,value\n")
    assert first.source_filename == "first.csv"
    assert second.source_filename == "second.csv"
    stored = get_last_analysis()
    assert stored is not None
    assert stored.source_filename == "second.csv"
    assert stored.metrics["total"] == 2


def test_in4_missing_required_column_detected():
    df = pd.DataFrame([{"incident_id": "INC-001"}])
    missing = validate_columns(df)
    assert "patient_id" in missing
    assert "clinic_id" in missing


def test_in5_empty_store_returns_none():
    assert get_last_analysis() is None


def test_in6_error_paths_do_not_expose_phi():
    df = pd.DataFrame(
        [
            {
                "incident_id": "INC-001",
                "date": "2025-01-01",
                "clinic_id": "US-TX-01",
                "country": "US",
                "category": "APPOINTMENT",
                "description": "Sensitive patient complaint text",
                "status": "OPEN",
                "patient_id": "PAT-000001",
                "satisfaction_score": "",
            }
        ]
    )
    missing = validate_columns(df.drop(columns=["patient_id"]))
    message = f"Invalid CSV format: missing required columns: {', '.join(missing)}"
    assert "PAT-000001" not in message
    assert "Sensitive patient complaint" not in message

    export_csv = metrics_to_csv_string(analyze(df))
    assert "PAT-000001" not in export_csv
    assert "Sensitive patient complaint" not in export_csv
    assert all("patient_id" not in label.lower() or "missing" in label.lower() for label in INVALID_RULE_LABELS.values())
