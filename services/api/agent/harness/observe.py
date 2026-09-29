"""Guardrail hits: type + name + run_id only. Never log question, answer, or PHI."""

from __future__ import annotations

import logging
import threading
from typing import Literal

logger = logging.getLogger("agent.harness")

GuardType = Literal["security", "content", "structural"]

_lock = threading.Lock()
_counts: dict[str, int] = {}

LABEL_TYPE: dict[str, GuardType] = {
    "injection": "security",
    "phi": "content",
    "personal": "content",
    "sensitive": "content",
    "casual": "content",
    "output_phi": "content",
    "output_leak": "security",
    "output_sensitive": "content",
    "output_redirect": "content",
    "structural": "structural",
}


def record(name: str, *, run_id: str, kind: GuardType | None = None) -> None:
    failure = kind or LABEL_TYPE.get(name, "content")
    key = f"{failure}:{name}"
    with _lock:
        _counts[key] = _counts.get(key, 0) + 1
    logger.info("guardrail hit type=%s name=%s run_id=%s", failure, name, run_id or "-")


def summary() -> dict[str, int]:
    with _lock:
        return dict(_counts)


def reset_counts() -> None:
    with _lock:
        _counts.clear()
