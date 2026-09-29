"""RFP vs vendor-pitch classifier. Deterministic fallback; optional LLM never required."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from data.pipelines.rfp_intake.extracts import infer_program_type

logger = logging.getLogger(__name__)

_SERVICE = re.compile(
    r"\b(?:occupational\s+health|corporate\s+wellness|wellness\s+program|"
    r"referral\s+(?:network|partnership))\b",
    re.I,
)
_RFP_SIGNAL = re.compile(r"\b(?:request\s+for\s+proposal|\brfp\b)\b", re.I)
_VENDOR = re.compile(
    r"\b(?:ehr|electronic\s+health\s+record|our\s+(?:software|platform|product)|"
    r"vendor\s+(?:pitch|demo)|buy\s+our|replace\s+your\s+ehr)\b",
    re.I,
)


def classify_rfp_fallback(markdown: str) -> dict[str, Any]:
    """Accept institutional occupational / wellness / referral requests; reject EHR vendor pitches."""
    text = markdown or ""
    has_service = bool(_SERVICE.search(text))
    has_rfp = bool(_RFP_SIGNAL.search(text))
    has_vendor = bool(_VENDOR.search(text))
    program_type = infer_program_type(text)

    if has_vendor and not has_service:
        return {
            "is_rfp": False,
            "reason": "Vendor product pitch, not a client RFP.",
            "program_type": "unknown",
        }
    if has_service or (has_rfp and not has_vendor):
        return {
            "is_rfp": True,
            "reason": "Institutional request for HealthCore services.",
            "program_type": program_type,
        }
    return {
        "is_rfp": False,
        "reason": "Document is not a HealthCore institutional RFP.",
        "program_type": "unknown",
    }


def _llm_classify(markdown: str) -> dict[str, Any] | None:
    key = (
        os.getenv("LLM_API_KEY")
        or os.getenv("RAG_API_KEY")
        or os.getenv("FOURGEEKS_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()
    if not key:
        return None
    base = (os.getenv("LLM_API_URL") or os.getenv("RAG_BASE_URL") or "https://api.openai.com/v1").rstrip(
        "/"
    )
    model = (os.getenv("LLM_MODEL") or os.getenv("RAG_MODEL") or "gpt-4o-mini").strip()
    excerpt = (markdown or "")[:6000]
    try:
        import httpx

        response = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Classify whether the document is a HealthCore institutional RFP "
                            "(occupational health, corporate wellness, or referral partnership). "
                            "Reject vendor EHR/software pitches. Return JSON "
                            '{"is_rfp": bool, "reason": str, "program_type": str}.'
                        ),
                    },
                    {"role": "user", "content": excerpt},
                ],
            },
            timeout=30.0,
        )
        if response.is_error:
            return None
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict) or "is_rfp" not in parsed:
            return None
        return {
            "is_rfp": bool(parsed["is_rfp"]),
            "reason": str(parsed.get("reason") or ""),
            "program_type": str(parsed.get("program_type") or infer_program_type(markdown)),
        }
    except Exception:
        logger.debug("LLM classifier unavailable; using fallback")
        return None


def classify_rfp(markdown: str) -> dict[str, Any]:
    llm = _llm_classify(markdown)
    if llm is not None:
        return llm
    return classify_rfp_fallback(markdown)
