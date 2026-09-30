"""Append-only node log. Summaries are statuses and trigger ids, never PHI text."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data.pipelines.paths import EVAL_DIR


def trace_dir() -> Path:
    override = os.getenv("RFP_APPROVAL_TRACE_DIR", "").strip()
    path = Path(override) if override else EVAL_DIR / "rfp_approval_traces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def event(node: str, department_id: str | None, input_summary: str, output_summary: str) -> dict[str, Any]:
    return {
        "node": node,
        "department_id": department_id,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "at": datetime.now(timezone.utc).isoformat(),
    }


def write_trace(ticket_id: str, events: list[dict[str, Any]]) -> None:
    ordered = sorted(events, key=lambda item: str(item.get("at") or ""))
    (trace_dir() / f"{ticket_id}.json").write_text(json.dumps(ordered, indent=2), encoding="utf-8")
