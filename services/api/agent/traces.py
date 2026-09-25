"""Persist queryable per-run traces. No chunk text, no PHI."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from agent.state import DeskAgentState

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def repo_root() -> Path:
    env = os.environ.get("HEALTHCORE_REPO_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[3]


def traces_dir() -> Path:
    path = repo_root() / "data" / "eval" / "agent_traces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def infer_path(state: DeskAgentState) -> list[str]:
    """Rebuild the executed node list from final state (edges are deterministic)."""
    if state.get("error"):
        return ["intake", "reject"]
    if not state.get("context"):
        return ["intake", "retrieve_policy", "refuse"]
    return ["intake", "retrieve_policy", "generate_policy"]


def build_trace(state: DeskAgentState) -> dict[str, Any]:
    context = state.get("context") or []
    error = state.get("error") or ""
    return {
        "run_id": state.get("run_id", ""),
        "path": infer_path(state),
        "question": state.get("question", ""),
        "context_sources": [
            str(row.get("source_document", ""))
            for row in context
            if isinstance(row, dict) and row.get("source_document")
        ],
        "answer": state.get("answer", ""),
        "error": error or None,
    }


def persist_trace(state: DeskAgentState) -> Path:
    payload = build_trace(state)
    run_id = payload["run_id"]
    if not run_id or not _UUID.match(run_id):
        raise ValueError("trace run_id must be a UUID")
    path = traces_dir() / f"{run_id}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load_trace(run_id: str) -> dict[str, Any] | None:
    if not _UUID.match(run_id):
        return None
    path = traces_dir() / f"{run_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
