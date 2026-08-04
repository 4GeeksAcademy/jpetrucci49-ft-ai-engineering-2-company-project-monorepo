from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.incidents.analysis import (
    BREAKDOWN_RULES,
    CATEGORIES,
    COUNTRIES,
    INVALID_RULE_LABELS,
    SCORE_LABELS,
    STATUSES,
)


@dataclass
class StoredAnalysis:
    source_filename: str
    analyzed_at: datetime
    metrics: dict
    csv_content: str


_last_result: StoredAnalysis | None = None


def save_analysis(
    source_filename: str,
    metrics: dict,
    csv_content: str,
) -> StoredAnalysis:
    global _last_result
    _last_result = StoredAnalysis(
        source_filename=source_filename,
        analyzed_at=datetime.now(UTC),
        metrics=metrics,
        csv_content=csv_content,
    )
    return _last_result


def get_last_analysis() -> StoredAnalysis | None:
    return _last_result


def metrics_to_response(stored: StoredAnalysis) -> dict:
    metrics = stored.metrics
    invalid_rules = list(BREAKDOWN_RULES)
    if metrics["invalid_counts"]["out_of_range_score"] > 0:
        invalid_rules.append("out_of_range_score")

    return {
        "source_filename": stored.source_filename,
        "analyzed_at": stored.analyzed_at.isoformat().replace("+00:00", "Z"),
        "totals": {
            "total": metrics["total"],
            "valid_count": metrics["valid_count"],
            "invalid_count": metrics["invalid_count"],
        },
        "invalid_breakdown": [
            {
                "rule": rule,
                "label": INVALID_RULE_LABELS[rule],
                "count": metrics["invalid_counts"][rule],
            }
            for rule in invalid_rules
        ],
        "categories": [
            {
                "code": category,
                "count": metrics["category_counts"][category],
                "percentage": metrics["category_pct"][category],
            }
            for category in CATEGORIES
        ],
        "statuses": [
            {
                "code": status,
                "count": metrics["status_counts"][status],
                "percentage": metrics["status_pct"][status],
            }
            for status in STATUSES
        ],
        "countries": [
            {
                "code": country,
                "count": metrics["country_counts"][country],
                "percentage": metrics["country_pct"][country],
            }
            for country in COUNTRIES
        ],
        "satisfaction": {
            "closed_total": metrics["closed_total"],
            "scored_total": metrics["scored_total"],
            "average_score": metrics["average_score"],
            "scores": [
                {
                    "score": score,
                    "label": SCORE_LABELS[score],
                    "count": metrics["score_counts"][score],
                }
                for score in range(1, 6)
            ],
        },
    }
