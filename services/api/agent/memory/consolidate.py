"""Cap, dedupe, and expire approved items. PHI is re-checked before keep."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from agent.memory.phi import contains_phi

ITEM_CAP = 20
ITEM_TTL = timedelta(days=90)

_SPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    return _SPACE.sub(" ", (text or "").strip().casefold())


def is_expired(updated_at: str, *, now: datetime | None = None) -> bool:
    moment = now or datetime.now(UTC)
    try:
        stamp = datetime.fromisoformat(updated_at)
    except ValueError:
        return True
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return stamp + ITEM_TTL < moment


def consolidate_items(rows: list[dict], *, now: datetime | None = None) -> list[dict]:
    kept: list[dict] = []
    seen: set[tuple[int, str, str]] = set()
    ordered = sorted(rows, key=lambda row: row.get("updated_at") or "", reverse=True)
    for row in ordered:
        text = row.get("text") or ""
        if contains_phi(text):
            continue
        if is_expired(row.get("updated_at") or "", now=now):
            continue
        key = (
            int(row.get("user_id") or 0),
            str(row.get("kind") or ""),
            normalize_text(text),
        )
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
        if len(kept) >= ITEM_CAP:
            break
    kept.sort(key=lambda row: row.get("updated_at") or "")
    return kept
