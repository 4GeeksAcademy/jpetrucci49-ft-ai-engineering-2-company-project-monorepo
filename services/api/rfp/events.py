"""In-process fan-out for RFP ticket registration notices.

One Uvicorn process. Each open stream owns a bounded queue. A full queue
drops that connection so ticket creation never waits on a slow listener.
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from collections.abc import AsyncIterator

KEEPALIVE_SECONDS = 15
_QUEUE_SIZE = 32

_lock = threading.Lock()
_subscribers: set[queue.Queue[str | None]] = set()
_next_id = 0


def publish_ticket_created(ticket_id: str, status: str) -> None:
    """Notify every open stream that a ticket row was committed."""
    global _next_id
    with _lock:
        _next_id += 1
        frame = _frame(
            _next_id,
            {
                "agent_id": "rfp_pipeline",
                "flow_id": ticket_id,
                "flow_type": "rfp_workflow",
                "ticket_id": ticket_id,
                "status": status,
            },
        )
        for subscriber in tuple(_subscribers):
            _offer(subscriber, frame)


def subscribe() -> queue.Queue[str | None]:
    subscriber: queue.Queue[str | None] = queue.Queue(maxsize=_QUEUE_SIZE)
    with _lock:
        _subscribers.add(subscriber)
    return subscriber


def unsubscribe(subscriber: queue.Queue[str | None]) -> None:
    with _lock:
        _subscribers.discard(subscriber)


def reset_hub() -> None:
    """Drop every listener. Tests use this so event ids start at 1."""
    global _next_id
    with _lock:
        for subscriber in tuple(_subscribers):
            _offer(subscriber, None)
            _subscribers.discard(subscriber)
        _next_id = 0


async def event_stream(subscriber: queue.Queue[str | None]) -> AsyncIterator[str]:
    try:
        yield ": ping\n\n"
        while True:
            frame = await asyncio.to_thread(_next_frame, subscriber)
            if frame is None:
                break
            yield frame
    finally:
        unsubscribe(subscriber)


def _next_frame(subscriber: queue.Queue[str | None]) -> str | None:
    try:
        return subscriber.get(timeout=KEEPALIVE_SECONDS)
    except queue.Empty:
        return ": ping\n\n"


def _offer(subscriber: queue.Queue[str | None], frame: str | None) -> None:
    try:
        subscriber.put_nowait(frame)
    except queue.Full:
        _drop(subscriber)


def _drop(subscriber: queue.Queue[str | None]) -> None:
    _subscribers.discard(subscriber)
    while True:
        try:
            subscriber.get_nowait()
        except queue.Empty:
            break
    try:
        subscriber.put_nowait(None)
    except queue.Full:
        pass


def _frame(event_id: int, payload: dict[str, str]) -> str:
    data = json.dumps(payload, separators=(",", ":"))
    return f"id: {event_id}\nevent: agent_status_changed\ndata: {data}\n\n"
