"""Deterministic metadata and per-department extracts. Never invent figures."""

from __future__ import annotations

import re
from typing import Any

DEPARTMENT_IDS = ("revenue", "clinical", "compliance")

_PROGRAM_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"occupational\s+health", re.I), "occupational_health"),
    (re.compile(r"corporate\s+wellness|wellness\s+program", re.I), "corporate_wellness"),
    (re.compile(r"referral\s+(?:network|partnership)", re.I), "referral_network"),
)

_US = re.compile(
    r"\b(?:united states|\bu\.?s\.?a?\.?\b|texas|austin|hipaa|\busd\b|\$)\b",
    re.I,
)
_UK = re.compile(
    r"\b(?:united kingdom|\buk\b|england|london|manchester|thames|uk gdpr|\bgbp\b|£)\b",
    re.I,
)
_POPULATION = re.compile(
    r"(\d{1,6})\s+(?:employees|students|staff|lives|members)",
    re.I,
)
_CLIENT_LINE = re.compile(
    r"(?:client|from|organization|company|employer|institution)\s*[:\-]\s*([^\n]+)",
    re.I,
)
_DEADLINE = re.compile(
    r"(?:deadline|due(?:\s+date)?|response by|by)\s*[:\-]?\s*"
    r"([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_BUDGET = re.compile(r"[\$£]\s?[\d,]+(?:\s*[-–]\s*[\$£]?[\d,]+)?")
_KNOWN_CLIENTS = (
    (re.compile(r"meridian\s+manufacturing", re.I), "Meridian Manufacturing"),
    (re.compile(r"thames\s+valley\s+university", re.I), "Thames Valley University"),
)
_HEADING = re.compile(r"^#\s+(.+)$", re.M)

_DEPT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "payment",
        "currency",
        "budget",
        "contract",
        "usd",
        "gbp",
        "pricing",
        "invoice",
        "month",
        "financial",
        "fee",
    ),
    "clinical": (
        "clinic",
        "staff",
        "capacity",
        "employee",
        "student",
        "on-site",
        "onsite",
        "satellite",
        "occupational",
        "wellness",
        "covered",
        "population",
        "referral",
    ),
    "compliance": (
        "hipaa",
        "gdpr",
        "baa",
        "dpa",
        "privacy",
        "phi",
        "patient data",
        "regulatory",
        "united states",
        "united kingdom",
        "business associate",
        "data processing",
    ),
}


def infer_program_type(text: str) -> str:
    for pattern, value in _PROGRAM_RULES:
        if pattern.search(text or ""):
            return value
    return "unknown"


def infer_country(text: str) -> str:
    blob = text or ""
    uk = bool(_UK.search(blob))
    us = bool(_US.search(blob))
    if uk and not us:
        return "UK"
    if us and not uk:
        return "US"
    if "thames" in blob.lower() or "£" in blob:
        return "UK"
    if "austin" in blob.lower() or "texas" in blob.lower():
        return "US"
    return "unknown"


def _client_name(text: str) -> str | None:
    blob = text or ""
    for pattern, name in _KNOWN_CLIENTS:
        if pattern.search(blob):
            return name
    match = _CLIENT_LINE.search(blob)
    if match:
        return match.group(1).strip().rstrip(".")
    heading = _HEADING.search(blob)
    if heading:
        title = heading.group(1).strip()
        if not re.search(r"request for proposal|\brfp\b", title, re.I):
            return title
    return None


def extract_metadata(markdown: str) -> dict[str, Any]:
    blob = markdown or ""
    country = infer_country(blob)
    population_match = _POPULATION.search(blob)
    budget_match = _BUDGET.search(blob)
    deadline_match = _DEADLINE.search(blob)
    currency = {"US": "USD", "UK": "GBP"}.get(country)
    return {
        "client_name": _client_name(blob),
        "client_country": country,
        "program_type": infer_program_type(blob),
        "covered_population": int(population_match.group(1)) if population_match else None,
        "deadline": deadline_match.group(1).strip() if deadline_match else None,
        "budget_range": budget_match.group(0).replace(" ", "") if budget_match else None,
        "currency": currency,
        "departments_needed": list(DEPARTMENT_IDS),
    }


def extract_for_department(markdown: str, department_id: str) -> str:
    blob = (markdown or "").strip()
    if department_id not in _DEPT_KEYWORDS:
        return ""
    if len(blob) <= 1200:
        return blob
    keywords = _DEPT_KEYWORDS[department_id]
    blocks = re.split(r"\n\s*\n", blob)
    hits = [block.strip() for block in blocks if any(key in block.lower() for key in keywords)]
    if not hits:
        return blob[:1500]
    return "\n\n".join(hits)[:4000]


def department_extracts(markdown: str) -> dict[str, str]:
    return {dept: extract_for_department(markdown, dept) for dept in DEPARTMENT_IDS}
