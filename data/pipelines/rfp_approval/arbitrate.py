"""CONTEXT §7 triggers. Fixed arbiters only — no LLM."""

from __future__ import annotations

import re
from typing import Any

from agent.memory.phi import contains_phi

PHI_STUB = "Content blocked pending Compliance review."
_CAPACITY = re.compile(r"(staff capacity|clinic count|headcount).{0,40}?(\d+)", re.IGNORECASE)

_BAA = {
    "trigger_id": "baa-dpa-mismatch",
    "arbiter": "Claire Whitfield",
    "arbiter_department_id": "compliance",
    "action": "request_changes",
    "instruction": "US client requires a Business Associate Agreement (BAA) clause.",
}
_DPA = {
    **_BAA,
    "instruction": "UK client requires a DPA referencing UK GDPR.",
}
_CURRENCY = {
    **_BAA,
    "instruction": "Pricing currency must match client country.",
}


def _record(base: dict[str, Any], affected: list[str]) -> dict[str, Any]:
    return {**base, "affected_departments": affected}


def capacity_figure(aspects: list[str], draft: str) -> int | None:
    blob = " ".join([*aspects, draft or ""])
    match = _CAPACITY.search(blob)
    if not match:
        return None
    return int(match.group(2))


def _phi(draft: str, evaluation: dict[str, Any]) -> bool:
    compliance = (evaluation or {}).get("compliance") or {}
    return bool(compliance.get("contains_phi") or contains_phi(draft or ""))


def _rule_ids(evaluation: dict[str, Any]) -> set[str]:
    compliance = (evaluation or {}).get("compliance") or {}
    return set(compliance.get("rule_ids") or [])


def _instrument_mismatch(country: str, draft: str, rules: set[str]) -> dict[str, Any] | None:
    upper = (draft or "").upper()
    if country == "US" and ("baa-us" in rules or ("BAA" not in upper and "BUSINESS ASSOCIATE" not in upper)):
        return _BAA
    if country == "UK" and ("dpa-uk" in rules or ("DPA" not in upper and "UK GDPR" not in upper)):
        return _DPA
    return None


def _currency_mismatch(country: str, draft: str, rules: set[str]) -> bool:
    if "currency-country" in rules:
        return True
    if country == "US" and re.search(r"\bGBP\b|£", draft or ""):
        return True
    if country == "UK" and re.search(r"\bUSD\b", draft or ""):
        return True
    return False


def triggers_for(
    department_id: str,
    *,
    drafts: dict[str, str],
    aspects: dict[str, list[str]],
    evaluations: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    """Triggers that block this department. ``phi-detected`` suppresses the others."""
    draft = drafts.get(department_id) or ""
    evaluation = evaluations.get(department_id) or {}
    if _phi(draft, evaluation):
        return [
            _record(
                {
                    "trigger_id": "phi-detected",
                    "arbiter": "Claire Whitfield",
                    "arbiter_department_id": "compliance",
                    "action": "request_changes",
                    "instruction": "Remove patient identifiers before this section can be approved.",
                },
                [department_id],
            )
        ]

    country = metadata.get("client_country") or "unknown"
    found: list[dict[str, Any]] = []
    rules = _rule_ids(evaluation)
    if department_id == "compliance":
        mismatch = _instrument_mismatch(country, draft, rules)
        if mismatch:
            found.append(_record(mismatch, ["compliance"]))
    if _currency_mismatch(country, draft, rules):
        found.append(_record(_CURRENCY, [department_id]))

    any_phi = any(_phi(drafts.get(dept) or "", evaluations.get(dept) or {}) for dept in drafts)
    population = metadata.get("covered_population")
    figure = capacity_figure(aspects.get("clinical") or [], drafts.get("clinical") or "")
    if (
        not any_phi
        and department_id in {"clinical", "revenue"}
        and isinstance(population, int)
        and figure is not None
        and figure < population
    ):
        found.append(
            _record(
                {
                    "trigger_id": "capacity-vs-population",
                    "arbiter": "Tom Callahan",
                    "arbiter_department_id": "revenue",
                    "action": "request_changes",
                    "instruction": "Reduce covered population or add sites. Do not invent a new figure.",
                },
                ["clinical", "revenue"],
            )
        )
    return found
