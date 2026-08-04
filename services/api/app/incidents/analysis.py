"""Shared incident CSV validation and analysis logic."""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

CLINIC_COUNTRIES: dict[str, str] = {
    "US-TX-01": "US",
    "US-TX-02": "US",
    "US-TX-03": "US",
    "US-FL-01": "US",
    "US-FL-02": "US",
    "US-FL-03": "US",
    "US-GA-01": "US",
    "US-GA-02": "US",
    "US-GA-03": "US",
    "UK-LON-01": "UK",
    "UK-LON-02": "UK",
    "UK-MAN-01": "UK",
}

CATEGORIES = (
    "APPOINTMENT",
    "BILLING",
    "CLINICAL_CARE",
    "ACCESSIBILITY",
    "ADMINISTRATIVE",
)

STATUSES = ("OPEN", "CLOSED", "DISCARDED")

COUNTRIES = ("US", "UK")

REQUIRED_COLUMNS = (
    "incident_id",
    "date",
    "clinic_id",
    "country",
    "category",
    "description",
    "status",
    "patient_id",
    "satisfaction_score",
)

PATIENT_ID_PATTERN = re.compile(r"^PAT-\d{6}$")

SCORE_LABELS = {
    1: "Very dissatisfied",
    2: "Dissatisfied",
    3: "Neutral",
    4: "Satisfied",
    5: "Very satisfied",
}

INVALID_RULE_LABELS = {
    "invalid_clinic_id": "Invalid or missing clinic_id",
    "country_clinic_mismatch": "Country/clinic mismatch",
    "invalid_category": "Invalid or missing category",
    "empty_description": "Empty description",
    "missing_patient_id": "Missing patient_id",
    "closed_no_score": "Closed case, no score",
    "out_of_range_score": "Out-of-range satisfaction score",
}

BREAKDOWN_RULES = (
    "invalid_clinic_id",
    "country_clinic_mismatch",
    "invalid_category",
    "empty_description",
    "missing_patient_id",
    "closed_no_score",
)


def _text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _parse_score(value: object) -> int | None | str:
    """Return score int, None if missing, or 'invalid' if present but not 1-5."""
    text = _text(value)
    if not text:
        return None
    try:
        numeric = float(text)
        if not numeric.is_integer():
            return "invalid"
        score = int(numeric)
    except ValueError:
        return "invalid"
    if 1 <= score <= 5:
        return score
    return "invalid"


def validate_record(row: pd.Series) -> list[str]:
    violations: list[str] = []

    clinic_id = _text(row.get("clinic_id"))
    country = _text(row.get("country"))
    category = _text(row.get("category"))
    description = _text(row.get("description"))
    status = _text(row.get("status"))
    patient_id = _text(row.get("patient_id"))
    score = _parse_score(row.get("satisfaction_score"))

    clinic_valid = clinic_id in CLINIC_COUNTRIES
    if not clinic_valid:
        violations.append("invalid_clinic_id")
    elif country != CLINIC_COUNTRIES[clinic_id]:
        violations.append("country_clinic_mismatch")

    if not category or category not in CATEGORIES:
        violations.append("invalid_category")

    if len(description) < 5:
        violations.append("empty_description")

    if not patient_id or not PATIENT_ID_PATTERN.match(patient_id):
        violations.append("missing_patient_id")

    if score == "invalid":
        violations.append("out_of_range_score")
    elif status == "CLOSED" and score is None:
        violations.append("closed_no_score")

    return violations


def _read_csv(source: io.BytesIO | Path) -> pd.DataFrame:
    return pd.read_csv(source, encoding="utf-8", dtype=str, keep_default_na=False)


def load_incidents_from_path(path: Path) -> pd.DataFrame:
    return _read_csv(path)


def load_incidents_from_bytes(content: bytes) -> pd.DataFrame:
    if not content.strip():
        raise ValueError("empty")
    try:
        return _read_csv(io.BytesIO(content))
    except UnicodeDecodeError as exc:
        raise ValueError("encoding") from exc
    except pd.errors.ParserError as exc:
        raise ValueError("parse") from exc


def validate_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in REQUIRED_COLUMNS if column not in df.columns]


def analyze(df: pd.DataFrame) -> dict:
    total = len(df)
    invalid_counts = {rule: 0 for rule in INVALID_RULE_LABELS}
    valid_rows: list[pd.Series] = []

    for _, row in df.iterrows():
        violations = validate_record(row)
        if violations:
            for rule in violations:
                invalid_counts[rule] += 1
        else:
            valid_rows.append(row)

    valid_df = pd.DataFrame(valid_rows)
    valid_count = len(valid_df)
    invalid_count = total - valid_count

    def pct(count: int) -> float:
        if valid_count == 0:
            return 0.0
        return round(count / valid_count * 100, 1)

    category_counts = {cat: 0 for cat in CATEGORIES}
    status_counts = {status: 0 for status in STATUSES}
    country_counts = {country: 0 for country in COUNTRIES}
    score_counts = {score: 0 for score in range(1, 6)}

    closed_total = 0
    scored_total = 0
    score_sum = 0

    if valid_count > 0:
        for _, row in valid_df.iterrows():
            category_counts[_text(row["category"])] += 1
            status_counts[_text(row["status"])] += 1
            country_counts[_text(row["country"])] += 1

            if _text(row["status"]) == "CLOSED":
                closed_total += 1
                score = _parse_score(row["satisfaction_score"])
                if isinstance(score, int):
                    scored_total += 1
                    score_sum += score
                    score_counts[score] += 1

    average_score = round(score_sum / scored_total, 2) if scored_total else 0.0

    return {
        "total": total,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "invalid_counts": invalid_counts,
        "category_counts": category_counts,
        "category_pct": {cat: pct(category_counts[cat]) for cat in CATEGORIES},
        "status_counts": status_counts,
        "status_pct": {status: pct(status_counts[status]) for status in STATUSES},
        "country_counts": country_counts,
        "country_pct": {country: pct(country_counts[country]) for country in COUNTRIES},
        "closed_total": closed_total,
        "scored_total": scored_total,
        "average_score": average_score,
        "score_counts": score_counts,
    }


def metrics_to_csv_rows(metrics: dict) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [
        {"metric": "total_records", "value": metrics["total"], "percentage": ""},
        {"metric": "valid_records", "value": metrics["valid_count"], "percentage": ""},
        {
            "metric": "invalid_records",
            "value": metrics["invalid_count"],
            "percentage": "",
        },
    ]

    for rule in INVALID_RULE_LABELS:
        rows.append(
            {
                "metric": f"invalid.{rule}",
                "value": metrics["invalid_counts"][rule],
                "percentage": "",
            }
        )

    for category in CATEGORIES:
        rows.append(
            {
                "metric": f"category.{category.lower()}",
                "value": metrics["category_counts"][category],
                "percentage": metrics["category_pct"][category],
            }
        )

    for status in STATUSES:
        rows.append(
            {
                "metric": f"status.{status.lower()}",
                "value": metrics["status_counts"][status],
                "percentage": metrics["status_pct"][status],
            }
        )

    for country in COUNTRIES:
        rows.append(
            {
                "metric": f"country.{country.lower()}",
                "value": metrics["country_counts"][country],
                "percentage": metrics["country_pct"][country],
            }
        )

    rows.extend(
        [
            {
                "metric": "satisfaction.scored_cases",
                "value": metrics["scored_total"],
                "percentage": "",
            },
            {
                "metric": "satisfaction.closed_total",
                "value": metrics["closed_total"],
                "percentage": "",
            },
            {
                "metric": "satisfaction.average",
                "value": metrics["average_score"],
                "percentage": "",
            },
        ]
    )

    for score in range(1, 6):
        rows.append(
            {
                "metric": f"satisfaction.score_{score}",
                "value": metrics["score_counts"][score],
                "percentage": "",
            }
        )

    return rows


def metrics_to_csv_string(metrics: dict) -> str:
    return pd.DataFrame(metrics_to_csv_rows(metrics)).to_csv(index=False)
