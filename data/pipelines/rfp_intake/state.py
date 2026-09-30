"""LangGraph state for ``rfp_intake``. No PHI in keys or intended values."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


def merge_maps(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    return {**(left or {}), **(right or {})}


class RfpIntakeState(TypedDict, total=False):
    ticket_id: str
    pdf_path: str
    markdown: str
    markdown_path: str
    is_rfp: bool
    discard_reason: str | None
    metadata: dict[str, Any]
    extracts: dict[str, str]
    worker_results: Annotated[dict[str, Any], merge_maps]
    synthesizer: dict[str, Any]
    phi_detected: bool
    error_code: str | None
