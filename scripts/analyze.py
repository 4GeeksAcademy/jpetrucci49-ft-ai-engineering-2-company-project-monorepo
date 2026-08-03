#!/usr/bin/env python3
"""HealthCore patient incident CSV analysis utility."""

from __future__ import annotations

import re
import sys
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


def load_incidents(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)


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


def print_report(metrics: dict, source_file: str) -> None:
    width = 60
    print("=" * width)
    print("  HEALTHCORE — PATIENT INCIDENT REPORT ANALYSIS")
    print(f"  Source file: {source_file}")
    print("=" * width)
    print()
    print(f"TOTAL RECORDS IN FILE .......... {metrics['total']}")
    print(f"  ├─ Valid records ................ {metrics['valid_count']}")
    print(f"  └─ Invalid / incomplete .......... {metrics['invalid_count']}")
    print()
    print("INVALID RECORDS BREAKDOWN")

    breakdown_rules = [
        "invalid_clinic_id",
        "country_clinic_mismatch",
        "invalid_category",
        "empty_description",
        "missing_patient_id",
        "closed_no_score",
    ]
    for index, rule in enumerate(breakdown_rules):
        label = INVALID_RULE_LABELS[rule]
        count = metrics["invalid_counts"][rule]
        dots = "." * max(1, 33 - len(label))
        last = index == len(breakdown_rules) - 1
        prefix = "└─" if last else "├─"
        print(f"  {prefix} {label} {dots} {count}")

    print()
    print("BREAKDOWN BY CATEGORY (valid records)")
    for index, category in enumerate(CATEGORIES):
        count = metrics["category_counts"][category]
        pct = metrics["category_pct"][category]
        dots = "." * max(1, 18 - len(category))
        last = index == len(CATEGORIES) - 1
        prefix = "└─" if last else "├─"
        print(f"  {prefix} {category} {dots} {count}  ({pct}%)")

    print()
    print("BREAKDOWN BY STATUS (valid records)")
    for index, status in enumerate(STATUSES):
        count = metrics["status_counts"][status]
        pct = metrics["status_pct"][status]
        dots = "." * max(1, 24 - len(status))
        last = index == len(STATUSES) - 1
        prefix = "└─" if last else "├─"
        print(f"  {prefix} {status} {dots} {count}  ({pct}%)")

    print()
    print("BREAKDOWN BY COUNTRY (valid records)")
    for index, country in enumerate(COUNTRIES):
        count = metrics["country_counts"][country]
        pct = metrics["country_pct"][country]
        dots = "." * max(1, 26 - len(country))
        last = index == len(COUNTRIES) - 1
        prefix = "└─" if last else "├─"
        print(f"  {prefix} {country} {dots} {count}  ({pct}%)")

    print()
    print("SATISFACTION INDEX (closed cases)")
    print(
        f"  Scored cases: {metrics['scored_total']} of {metrics['closed_total']}"
    )
    print(f"  Average score: {metrics['average_score']:.2f} / 5.00")
    for index, score in enumerate(range(1, 6)):
        label = SCORE_LABELS[score]
        count = metrics["score_counts"][score]
        dots = "." * max(1, 33 - len(f"Score {score} ({label})"))
        last = index == 4
        prefix = "└─" if last else "├─"
        print(f"  {prefix} Score {score} ({label}) {dots} {count}")

    print()
    print("=" * width)


def export_csv(metrics: dict, path: Path) -> None:
    rows: list[dict[str, object]] = [
        {"metric": "total_records", "value": metrics["total"], "percentage": ""},
        {"metric": "valid_records", "value": metrics["valid_count"], "percentage": ""},
        {
            "metric": "invalid_records",
            "value": metrics["invalid_count"],
            "percentage": "",
        },
    ]

    for rule, label in INVALID_RULE_LABELS.items():
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

    rows.append(
        {
            "metric": "satisfaction.scored_cases",
            "value": metrics["scored_total"],
            "percentage": "",
        }
    )
    rows.append(
        {
            "metric": "satisfaction.closed_total",
            "value": metrics["closed_total"],
            "percentage": "",
        }
    )
    rows.append(
        {
            "metric": "satisfaction.average",
            "value": metrics["average_score"],
            "percentage": "",
        }
    )

    for score in range(1, 6):
        rows.append(
            {
                "metric": f"satisfaction.score_{score}",
                "value": metrics["score_counts"][score],
                "percentage": "",
            }
        )

    pd.DataFrame(rows).to_csv(path, index=False)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <path-to-incidents.csv>", file=sys.stderr)
        return 1

    csv_path = Path(sys.argv[1])
    if not csv_path.is_file():
        print(f"Error: file not found or not readable: {csv_path}", file=sys.stderr)
        return 1

    try:
        df = load_incidents(csv_path)
    except OSError as exc:
        print(f"Error: unable to read file: {exc}", file=sys.stderr)
        return 1

    metrics = analyze(df)
    print_report(metrics, csv_path.name)

    try:
        answer = input("Export results to CSV? [y / n]: ").strip().lower()
    except EOFError:
        answer = "n"

    if answer == "y":
        export_csv(metrics, Path("results.csv"))
        print("Results exported to results.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
