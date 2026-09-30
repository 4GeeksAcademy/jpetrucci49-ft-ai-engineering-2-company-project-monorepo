"""Per-department workers and synthesizer. Facts from metadata + extract only."""

from __future__ import annotations

import re
from typing import Any

from agent.memory.phi import contains_phi

DEPARTMENT_OWNERS: dict[str, str] = {
    "revenue": "Tom Callahan",
    "clinical": "Dr. Marcus Reid",
    "compliance": "Claire Whitfield",
}

DEPARTMENT_LABELS: dict[str, str] = {
    "revenue": "Revenue Cycle",
    "clinical": "Clinical Operations",
    "compliance": "Compliance and Data Governance",
}

_CONTRACT_MONTHS = re.compile(r"(\d{1,2})\s*[- ]\s*month", re.I)
_ON_SITE = re.compile(r"on[-\s]?site", re.I)
_SATELLITE = re.compile(r"satellite\s+clinic", re.I)
_PAYMENT = re.compile(r"(?:payment|invoic\w+|net\s+\d+)", re.I)


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != "unknown"


def _safe_aspects(items: list[str]) -> list[str]:
    clean: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or contains_phi(text):
            continue
        clean.append(text)
    return clean


def run_worker(
    department_id: str,
    metadata: dict[str, Any],
    extract: str,
    *,
    phi_detected: bool = False,
) -> dict[str, Any]:
    """Return key_aspects + open_questions. Never invent headcount, budget, or clinics."""
    meta = metadata or {}
    blob = extract or ""
    aspects: list[str] = []
    questions: list[str] = []

    if department_id == "revenue":
        if _present(meta.get("currency")):
            aspects.append(f"Quote currency is {meta['currency']} (from client country).")
        if _present(meta.get("budget_range")):
            aspects.append(f"RFP states a reference budget of {meta['budget_range']}.")
        else:
            questions.append("What budget or fee structure should Revenue Cycle use?")
        months = _CONTRACT_MONTHS.search(blob)
        if months:
            aspects.append(f"Contract length stated as {months.group(1)} months.")
        if _PAYMENT.search(blob):
            aspects.append("Payment or invoicing terms appear in the RFP extract.")
        else:
            questions.append("What payment structure and invoicing terms apply?")
        if _present(meta.get("client_name")):
            aspects.append(f"Institutional client: {meta['client_name']}.")

    elif department_id == "clinical":
        population = meta.get("covered_population")
        if isinstance(population, int) and population > 0:
            aspects.append(f"Covered population stated as {population}.")
        else:
            questions.append("What covered population / headcount must Clinical Operations staff for?")
        if _ON_SITE.search(blob):
            aspects.append("On-site occupational or wellness coverage is requested.")
        if _SATELLITE.search(blob):
            aspects.append("A satellite clinic / referral site is mentioned.")
        if _present(meta.get("program_type")):
            aspects.append(f"Program type: {meta['program_type'].replace('_', ' ')}.")
        if not _ON_SITE.search(blob) and not _SATELLITE.search(blob):
            questions.append("Which clinics and staff capacity can cover this contract?")

    elif department_id == "compliance":
        country = meta.get("client_country")
        if country == "US":
            aspects.append("US client — proposal must include a Business Associate Agreement (BAA).")
        elif country == "UK":
            aspects.append("UK client — proposal must include a DPA referencing UK GDPR.")
        else:
            questions.append("Is the client in the US (BAA / HIPAA) or the UK (DPA / UK GDPR)?")
        if phi_detected:
            aspects.append(
                "PHI indicators were detected and redacted — Claire Whitfield must review before any draft."
            )
        aspects.append("Compliance review is mandatory on every institutional RFP.")

    return {
        "department_id": department_id,
        "owner": DEPARTMENT_OWNERS[department_id],
        "key_aspects": _safe_aspects(aspects),
        "open_questions": _safe_aspects(questions),
    }


def synthesize(
    ticket_id: str,
    metadata: dict[str, Any],
    worker_results: dict[str, Any],
    *,
    phi_detected: bool = False,
) -> dict[str, Any]:
    departments: list[dict[str, Any]] = []
    lines: list[str] = []
    for dept in ("revenue", "clinical", "compliance"):
        raw = worker_results.get(dept) if isinstance(worker_results, dict) else None
        if not isinstance(raw, dict):
            raw = run_worker(dept, metadata, "", phi_detected=phi_detected)
        entry = {
            "department_id": dept,
            "owner": DEPARTMENT_OWNERS[dept],
            "key_aspects": _safe_aspects(list(raw.get("key_aspects") or [])),
            "open_questions": _safe_aspects(list(raw.get("open_questions") or [])),
        }
        departments.append(entry)
        ask = entry["key_aspects"][:2] or entry["open_questions"][:2]
        lines.append(
            f"Ask {entry['owner']} ({DEPARTMENT_LABELS[dept]}): " + ("; ".join(ask) if ask else "review the intake.")
        )

    summary = " ".join(lines)
    if phi_detected:
        summary += " PHI was flagged — do not circulate the original PDF text; Compliance reviews first."

    meta_out = {k: v for k, v in (metadata or {}).items() if k != "readability"}
    return {
        "ticket_id": ticket_id,
        "phi_detected": phi_detected,
        "metadata": meta_out,
        "departments": departments,
        "synthesizer_summary": summary,
    }
