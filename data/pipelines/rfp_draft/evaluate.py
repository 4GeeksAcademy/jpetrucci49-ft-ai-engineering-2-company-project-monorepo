"""Readability, relevance, and CONTEXT §5 compliance evaluators."""

from __future__ import annotations

import re
from typing import Any

from agent.memory.phi import contains_phi
from data.pipelines.rfp_intake.readability import compute_readability

MAX_DRAFT_ITERATIONS = 3
MIN_DRAFT_WORDS = 40
MIN_FLESCH_EASE = 40.0

_STOP = frozenset(
    {
        "the",
        "and",
        "from",
        "that",
        "this",
        "with",
        "for",
        "into",
        "stated",
        "intake",
        "must",
        "will",
        "have",
        "been",
        "they",
        "them",
        "their",
        "as",
        "are",
        "was",
        "were",
        "not",
    }
)
_NUMBER = re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b")


def word_count(text: str) -> int:
    return len((text or "").split())


def evaluate_readability(draft: str) -> dict[str, Any]:
    blob = (draft or "").strip()
    count = word_count(blob)
    scores = compute_readability(blob) if count >= 50 else {}
    if count < MIN_DRAFT_WORDS:
        return {
            "pass": False,
            "score": scores,
            "details": f"Draft has {count} words; need at least {MIN_DRAFT_WORDS} for a reviewable section.",
        }
    ease = scores.get("flesch_reading_ease")
    if ease is None:
        return {"pass": True, "score": scores, "details": "Word count met; readability metrics unavailable."}
    if float(ease) < MIN_FLESCH_EASE:
        return {
            "pass": False,
            "score": scores,
            "details": f"flesch_reading_ease {ease:.1f} is below {MIN_FLESCH_EASE:.0f}.",
        }
    return {"pass": True, "score": scores, "details": f"flesch_reading_ease {float(ease):.1f}."}


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(token) > 3 and token not in _STOP
    ]


def aspect_reflected(aspect: str, draft: str) -> bool:
    tokens = _tokens(aspect)
    if not tokens:
        return True
    blob = (draft or "").lower()
    hits = sum(1 for token in tokens if token in blob)
    return hits >= max(1, (len(tokens) + 1) // 2)


def evaluate_relevance(draft: str, key_aspects: list[str]) -> dict[str, Any]:
    missing = [aspect for aspect in key_aspects if aspect and not aspect_reflected(aspect, draft)]
    return {"pass": not missing, "missing_aspects": missing}


def _allowed_numbers(metadata: dict[str, Any], key_aspects: list[str]) -> set[str]:
    allowed: set[str] = set()
    population = metadata.get("covered_population")
    if isinstance(population, int):
        allowed.add(str(population))
    for blob in [str(metadata.get("deadline") or ""), str(metadata.get("budget_range") or ""), *key_aspects]:
        allowed.update(_NUMBER.findall(blob.replace(",", "")))
    return {item.replace(",", "") for item in allowed}


def evaluate_compliance(
    draft: str,
    *,
    department_id: str,
    metadata: dict[str, Any],
    key_aspects: list[str],
) -> dict[str, Any]:
    rule_ids: list[str] = []
    violations: list[str] = []
    country = metadata.get("client_country") or "unknown"
    blob = draft or ""
    upper = blob.upper()

    phi = contains_phi(blob)
    if phi:
        rule_ids.append("no-phi")
        violations.append("Draft contains patient identifiers or diagnosis language.")

    if department_id == "compliance":
        if country == "US" and "BAA" not in upper and "BUSINESS ASSOCIATE" not in upper:
            rule_ids.append("baa-us")
            violations.append("US client requires a Business Associate Agreement (BAA) clause.")
        if country == "UK" and "DPA" not in upper and "UK GDPR" not in upper:
            rule_ids.append("dpa-uk")
            violations.append("UK client requires a DPA referencing UK GDPR.")

    if country == "US" and re.search(r"\bGBP\b|£", blob):
        rule_ids.append("currency-country")
        violations.append("US client drafts must not quote GBP.")
    if country == "UK" and re.search(r"\bUSD\b", blob):
        rule_ids.append("currency-country")
        violations.append("UK client drafts must not quote USD.")

    allowed = _allowed_numbers(metadata, key_aspects)
    invented = []
    for raw in _NUMBER.findall(blob.replace(",", "")):
        if raw not in allowed and not re.fullmatch(r"20\d{2}", raw):
            invented.append(raw)
    large_invented = [item for item in invented if float(item) >= 10]
    if large_invented:
        rule_ids.append("no-invented-figures")
        violations.append(f"Draft introduces figures not in the handoff: {', '.join(large_invented)}.")

    unique_rules = list(dict.fromkeys(rule_ids))
    return {
        "pass": not unique_rules,
        "rule_ids": unique_rules,
        "violations": violations,
        "contains_phi": phi,
    }


def combine_evaluation(
    department_id: str,
    parts: dict[str, Any],
    *,
    iteration: int,
    capped: bool = False,
) -> dict[str, Any]:
    readability = dict(parts.get("readability") or {"pass": False, "score": {}, "details": "missing"})
    relevance = dict(parts.get("relevance") or {"pass": False, "missing_aspects": ["evaluation incomplete"]})
    compliance = dict(
        parts.get("compliance")
        or {"pass": False, "rule_ids": [], "violations": ["evaluation incomplete"], "contains_phi": False}
    )
    overall = bool(readability.get("pass") and relevance.get("pass") and compliance.get("pass"))
    bits: list[str] = []
    if not readability.get("pass"):
        bits.append(str(readability.get("details") or "Lengthen and simplify the section (readability)."))
    if not relevance.get("pass"):
        missing = relevance.get("missing_aspects") or []
        bits.append("Restate these intake aspects: " + "; ".join(str(item) for item in missing[:4]))
    if not compliance.get("pass"):
        rules = compliance.get("rule_ids") or []
        viol = compliance.get("violations") or []
        bits.append("Fix compliance " + ", ".join(rules) + (": " + viol[0] if viol else "."))
    feedback = " ".join(bits).strip() if bits else ""
    if feedback.lower() in {"please improve the draft.", "improve the draft"}:
        feedback = "Named evaluation checks failed; address the listed rule ids and missing aspects."
    return {
        "department_id": department_id,
        "readability": readability,
        "relevance": relevance,
        "compliance": compliance,
        "overall_pass": overall,
        "feedback_for_generator": feedback,
        "needs_human_review": bool(capped and not overall),
        "iteration": iteration,
    }
