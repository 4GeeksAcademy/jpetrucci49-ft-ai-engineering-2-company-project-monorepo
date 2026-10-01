"""Desk chat sessions. One generation per session, fan-out to every open socket."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

from agent.graph import run_desk_agent
from auth.security import decode_access_token
from auth.services import users as user_service
from data.pipelines.rag import (
    reset_stream_cancel,
    reset_stream_sink,
    set_stream_cancel,
    set_stream_sink,
)
from jwt.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)

AGENT_ID = "compliance_assistant"
FLOW_TYPE = "chat_session"
_QUEUE_SIZE = 32

_lock = threading.Lock()
_sessions: dict[str, "ChatSession"] = {}


@dataclass
class ChatMessage:
    id: str
    role: str
    text: str
    status: str


@dataclass
class ChatSession:
    session_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    subscribers: set[queue.Queue] = field(default_factory=set)
    cancel: threading.Event = field(default_factory=threading.Event)
    running: bool = False
    pending_input: str | None = None
    pending_user_id: int = 0
    guard: threading.Lock = field(default_factory=threading.Lock)


def reset_chat_sessions() -> None:
    with _lock:
        for session in _sessions.values():
            session.cancel.set()
        _sessions.clear()


def produce_answer(
    question: str,
    *,
    user_id: int,
    run_id: str,
    sink,
    cancel: threading.Event,
) -> str:
    """Run one desk turn. Tests replace this so the suite never calls a model."""
    sink_token = set_stream_sink(sink)
    cancel_token = set_stream_cancel(cancel)
    try:
        result = run_desk_agent(question, user_id=user_id, run_id=run_id)
    finally:
        reset_stream_sink(sink_token)
        reset_stream_cancel(cancel_token)
    return str(result.get("answer") or "")


def user_from_token(token: str):
    try:
        user_id = decode_access_token(token)
    except (InvalidTokenError, ValueError, KeyError):
        return None
    user = user_service.get_user_by_id(user_id)
    if user is None or not user.is_active:
        return None
    return user


async def serve_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id = (websocket.query_params.get("session_id") or "").strip()
    if not session_id:
        await websocket.close(code=1008)
        return
    token = websocket.query_params.get("token") or ""
    if not token:
        token = await _auth_frame_token(websocket)
        if token is None:
            return
    user = user_from_token(token)
    if user is None:
        await websocket.close(code=1008)
        return

    session = _get_session(session_id)
    subscriber, history = _open_subscriber(session)
    pump: asyncio.Task | None = None
    try:
        await websocket.send_json(history)
        pump = asyncio.create_task(_pump(websocket, subscriber))
        while True:
            raw = await websocket.receive_text()
            await asyncio.to_thread(apply_client_frame, session, user.id, raw)
    except WebSocketDisconnect:
        pass
    finally:
        if pump is not None:
            pump.cancel()
        _unsubscribe(session, subscriber)


def apply_client_frame(session: ChatSession, user_id: int, raw: str) -> None:
    try:
        frame = json.loads(raw)
    except json.JSONDecodeError:
        return
    if not isinstance(frame, dict):
        return
    kind = frame.get("type")
    if kind == "user_message":
        text = str(frame.get("text") or "").strip()
        if text:
            _enqueue_turn(session, user_id, text)
    elif kind == "interrupt":
        text = str(frame.get("new_input") or "").strip()
        _interrupt(session, user_id, text)


def _enqueue_turn(session: ChatSession, user_id: int, text: str) -> None:
    with session.guard:
        if session.running:
            session.cancel.set()
            session.pending_input = text
            session.pending_user_id = user_id
            return
        _start_locked(session, user_id, text)


def _interrupt(session: ChatSession, user_id: int, new_input: str) -> None:
    with session.guard:
        if session.running:
            session.cancel.set()
            session.pending_input = new_input or None
            session.pending_user_id = user_id
            return
        if new_input:
            _start_locked(session, user_id, new_input)


def _start_locked(session: ChatSession, user_id: int, text: str) -> None:
    session.messages.append(ChatMessage(id=str(uuid.uuid4()), role="user", text=text, status="completed"))
    assistant = ChatMessage(id=str(uuid.uuid4()), role="assistant", text="", status="")
    session.messages.append(assistant)
    session.cancel = threading.Event()
    session.running = True
    session.pending_input = None
    thread = threading.Thread(
        target=_generate,
        args=(session, assistant.id, text, user_id),
        daemon=True,
    )
    thread.start()


def _generate(session: ChatSession, message_id: str, question: str, user_id: int) -> None:
    chunks: list[str] = []
    cancel = session.cancel

    def sink(delta: str) -> None:
        if cancel.is_set():
            return
        chunks.append(delta)
        with session.guard:
            message = _find(session, message_id)
            if message is not None:
                message.text += delta
        _publish(
            session,
            {
                "type": "token_chunk",
                "session_id": session.session_id,
                "message_id": message_id,
                "text": delta,
            },
        )

    final = ""
    failed = False
    try:
        final = produce_answer(
            question,
            user_id=user_id,
            run_id=str(uuid.uuid4()),
            sink=sink,
            cancel=cancel,
        )
    except Exception:
        logger.exception("desk chat generation failed")
        failed = True
        final = "".join(chunks)

    if not cancel.is_set() and not chunks and final:
        sink(final)

    streamed = "".join(chunks)
    pending: str | None = None
    pending_user = user_id
    with session.guard:
        message = _find(session, message_id)
        if cancel.is_set():
            if message is not None:
                message.text = streamed or message.text
                message.status = "interrupted"
            frame: dict = {
                "type": "generation_interrupted",
                "session_id": session.session_id,
                "message_id": message_id,
                "status": "interrupted",
            }
        else:
            if message is not None:
                message.text = final or streamed
                message.status = "completed"
            frame = {
                "type": "generation_completed",
                "session_id": session.session_id,
                "message_id": message_id,
                "status": "completed",
            }
            stored = message.text if message is not None else final
            if stored != streamed:
                frame["text"] = stored
        pending = session.pending_input
        pending_user = session.pending_user_id
        session.pending_input = None
        session.running = False
    if failed and not cancel.is_set():
        _publish(session, {"type": "error", "detail": "Unable to answer from the knowledge base."})
    _publish(session, frame)
    if pending:
        _enqueue_turn(session, pending_user, pending)


def _history_frame(session: ChatSession) -> dict:
    messages = [_message_row(message) for message in session.messages]
    return {
        "type": "history",
        "session_id": session.session_id,
        "flow_id": session.session_id,
        "agent_id": AGENT_ID,
        "flow_type": FLOW_TYPE,
        "messages": messages,
    }


def _get_session(session_id: str) -> ChatSession:
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            session = ChatSession(session_id=session_id)
            _sessions[session_id] = session
        return session


def _open_subscriber(session: ChatSession) -> tuple[queue.Queue, dict]:
    subscriber: queue.Queue = queue.Queue(maxsize=_QUEUE_SIZE)
    with session.guard:
        history = _history_frame(session)
        session.subscribers.add(subscriber)
    return subscriber, history


def _message_row(message: ChatMessage) -> dict:
    row = {"id": message.id, "role": message.role, "text": message.text}
    if message.status in {"completed", "interrupted"}:
        row["status"] = message.status
    return row


def _unsubscribe(session: ChatSession, subscriber: queue.Queue) -> None:
    with session.guard:
        session.subscribers.discard(subscriber)
    try:
        subscriber.put_nowait(None)
    except queue.Full:
        pass


def _publish(session: ChatSession, frame: dict) -> None:
    with session.guard:
        subscribers = tuple(session.subscribers)
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(frame)
        except queue.Full:
            with session.guard:
                session.subscribers.discard(subscriber)
            try:
                subscriber.put_nowait(None)
            except queue.Full:
                pass


def _find(session: ChatSession, message_id: str) -> ChatMessage | None:
    for message in session.messages:
        if message.id == message_id:
            return message
    return None


async def _auth_frame_token(websocket: WebSocket) -> str | None:
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        await websocket.close(code=1008)
        return None
    try:
        frame = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.close(code=1008)
        return None
    if not isinstance(frame, dict) or frame.get("type") != "auth":
        await websocket.close(code=1008)
        return None
    return str(frame.get("token") or "")


async def _pump(websocket: WebSocket, subscriber: queue.Queue) -> None:
    try:
        while True:
            frame = await asyncio.to_thread(subscriber.get)
            if frame is None:
                break
            await websocket.send_json(frame)
    except (WebSocketDisconnect, RuntimeError):
        return
