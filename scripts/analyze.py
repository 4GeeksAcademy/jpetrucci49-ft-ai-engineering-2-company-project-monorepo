#!/usr/bin/env python3
"""HealthCore patient incident CSV analysis utility (CLI)."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow imports from services/api when running from repo root.
_API_ROOT = Path(__file__).resolve().parents[1] / "services" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from app.incidents.analysis import (  # noqa: E402
    BREAKDOWN_RULES,
    CATEGORIES,
    COUNTRIES,
    INVALID_RULE_LABELS,
    SCORE_LABELS,
    STATUSES,
    analyze,
    load_incidents_from_path,
    metrics_to_csv_rows,
)

import pandas as pd  # noqa: E402


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

    for index, rule in enumerate(BREAKDOWN_RULES):
        label = INVALID_RULE_LABELS[rule]
        count = metrics["invalid_counts"][rule]
        dots = "." * max(1, 33 - len(label))
        last = index == len(BREAKDOWN_RULES) - 1
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
    print(f"  Scored cases: {metrics['scored_total']} of {metrics['closed_total']}")
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
    pd.DataFrame(metrics_to_csv_rows(metrics)).to_csv(path, index=False)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <path-to-incidents.csv>", file=sys.stderr)
        return 1

    csv_path = Path(sys.argv[1])
    if not csv_path.is_file():
        print(f"Error: file not found or not readable: {csv_path}", file=sys.stderr)
        return 1

    try:
        df = load_incidents_from_path(csv_path)
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
