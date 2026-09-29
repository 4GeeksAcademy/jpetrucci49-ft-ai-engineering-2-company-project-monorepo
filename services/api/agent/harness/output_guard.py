"""Scan the coordinator-facing answer before HTTP. Prompt-only PHI rules are not enough."""

from __future__ import annotations

from data.pipelines.rag import NO_INFORMATION

from agent.harness.input_guard import COMPLIANCE_REDIRECT, SENSITIVE_REFUSE
from agent.harness.isolate import BEGIN_UNTRUSTED
from agent.harness.observe import record
from agent.memory.phi import contains_phi_or_quasi
from agent.tools.incidents import TICKET_FALLBACK
from agent.tools.inventory import STOCK_FALLBACK

OUTPUT_PHI_REFUSE = (
    "I can't return that answer because it included patient identifiers or PHI. "
    "Please ask the policy question without identifiable details."
)
LEAK_REFUSE = (
    "I can't reveal internal instructions. " + COMPLIANCE_REDIRECT
)

_LEAK_MARKERS = (
    "never equal in authority",
    "BEGIN_UNTRUSTED_SOURCE",
    "user text is never",
    "ignore isolation",
    "claire whitfield / compliance",
)
_SENSITIVE_OUT = (
    "how many records were",
    "records were exposed",
    "under-investigation breach at",
    "monthly rate in the baa",
    "dpa commercial",
)


def apply_output_guard(
    answer: object,
    *,
    run_id: str,
    intent: str = "",
    input_label: str = "domain",
) -> tuple[str, str | None]:
    if not isinstance(answer, str) or not answer.strip():
        record("structural", run_id=run_id)
        if intent in {"incident", "both"}:
            return TICKET_FALLBACK, "structural"
        if intent in {"inventory", "inventory_rag"}:
            return STOCK_FALLBACK, "structural"
        return NO_INFORMATION, "structural"
    text = answer.strip()
    if contains_phi_or_quasi(text):
        record("output_phi", run_id=run_id)
        return OUTPUT_PHI_REFUSE, "output_phi"
    lowered = text.casefold()
    if (
        any(marker in lowered for marker in _LEAK_MARKERS)
        or (BEGIN_UNTRUSTED in text and "ignore" in lowered)
        or "ignore your instructions" in lowered
    ):
        record("output_leak", run_id=run_id)
        return LEAK_REFUSE, "output_leak"
    if any(marker in lowered for marker in _SENSITIVE_OUT):
        record("output_sensitive", run_id=run_id)
        return SENSITIVE_REFUSE, "output_sensitive"
    if input_label == "casual" and "healthcore" not in lowered:
        record("output_redirect", run_id=run_id)
        return f"{text}\n\n{COMPLIANCE_REDIRECT}", "output_redirect"
    return text, None
