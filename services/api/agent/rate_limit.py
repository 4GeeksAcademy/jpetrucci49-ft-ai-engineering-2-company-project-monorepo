"""In-process limit for POST /agent/query. One window per process; no shared store."""

from __future__ import annotations

import threading
import time

WINDOW_SECONDS = 60.0
MAX_REQUESTS = 10
RATE_LIMIT_DETAIL = "Too many agent queries. Try again in a minute."

_lock = threading.Lock()
_hits: dict[int, list[float]] = {}


def _now() -> float:
    return time.monotonic()


def allow_agent_query(user_id: int, *, now: float | None = None) -> bool:
    """Allow up to 10 calls in a 60-second sliding window for this user id."""
    clock = _now() if now is None else now
    cutoff = clock - WINDOW_SECONDS
    with _lock:
        recent = [stamp for stamp in _hits.get(user_id, []) if stamp > cutoff]
        if len(recent) >= MAX_REQUESTS:
            _hits[user_id] = recent
            return False
        recent.append(clock)
        _hits[user_id] = recent
        return True


def reset_agent_query_limits() -> None:
    with _lock:
        _hits.clear()
