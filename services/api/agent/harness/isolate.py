"""Untrusted RAG/tool text. Never treat wrapped content as system instructions."""

from __future__ import annotations

BEGIN_UNTRUSTED = "BEGIN_UNTRUSTED_SOURCE"
END_UNTRUSTED = "END_UNTRUSTED_SOURCE"


def wrap_text(text: str) -> str:
    body = text or ""
    if BEGIN_UNTRUSTED in body:
        return body
    return f"{BEGIN_UNTRUSTED}\n{body}\n{END_UNTRUSTED}"


def wrap_context(rows: list[dict]) -> list[dict]:
    wrapped: list[dict] = []
    for row in rows:
        item = dict(row)
        item["text"] = wrap_text(str(item.get("text") or ""))
        wrapped.append(item)
    return wrapped


def is_wrapped(text: str) -> bool:
    blob = text or ""
    return BEGIN_UNTRUSTED in blob and END_UNTRUSTED in blob
