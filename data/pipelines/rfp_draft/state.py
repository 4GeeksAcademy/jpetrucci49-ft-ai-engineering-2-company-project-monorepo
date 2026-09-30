"""LangGraph state for ``rfp_draft``. No PHI, no PDF text."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


def merge_eval_parts(
    left: dict[str, dict[str, Any]] | None,
    right: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {key: dict(value) for key, value in (left or {}).items()}
    for dept, parts in (right or {}).items():
        bucket = dict(merged.get(dept) or {})
        bucket.update(parts)
        merged[dept] = bucket
    return merged


def merge_maps(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    return {**(left or {}), **(right or {})}


class RfpDraftState(TypedDict, total=False):
    ticket_id: str
    handoff: dict[str, Any]
    iteration: Annotated[dict[str, int], merge_maps]
    drafts: Annotated[dict[str, str], merge_maps]
    eval_parts: Annotated[dict[str, dict[str, Any]], merge_eval_parts]
    results: dict[str, Any]
    feedback: Annotated[dict[str, str], merge_maps]
    pending: list[str]
    error_code: str | None
