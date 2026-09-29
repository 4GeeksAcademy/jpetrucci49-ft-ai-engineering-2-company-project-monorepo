"""TinyDB approved items, pending proposal, and decision audit."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from tinydb import Query, TinyDB

from agent.memory.classify import classify_memory_decision
from agent.memory.consolidate import consolidate_items
from agent.memory.phi import contains_phi

API_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = API_ROOT / "agent_memory.json"
ITEMS_TABLE = "items"
DECISIONS_TABLE = "decisions"
PENDING_TABLE = "pending"
PENDING_TTL = timedelta(hours=24)
REDACTED = "[redacted]"

MemoryKind = Literal["clinic_protocol", "incident_pattern", "presentation_pref"]
MemoryOutcome = Literal[
    "approved",
    "rejected",
    "discarded_unclear",
    "discarded_phi",
    "discarded_expired",
]

_db: TinyDB | None = None


class MemoryItem(BaseModel):
    id: int
    user_id: int
    kind: MemoryKind
    clinic: str = ""
    text: str
    created_at: str
    updated_at: str


class MemoryProposal(BaseModel):
    text: str
    kind: MemoryKind
    clinic: str = ""
    why: str = ""


class PendingProposal(BaseModel):
    proposal_id: str
    user_id: int
    text: str
    kind: MemoryKind
    clinic: str = ""
    why: str = ""
    created_at: str
    source_run_id: str = ""
    source_question: str = ""


class ResolveResult(BaseModel):
    outcome: MemoryOutcome | None = None
    proposal_id: str | None = None
    skipped: bool = False
    phi_refusal: bool = False


def get_db_path() -> Path:
    configured = os.environ.get("AGENT_MEMORY_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    return DEFAULT_DB_PATH


def get_db() -> TinyDB:
    global _db
    if _db is None:
        _db = TinyDB(get_db_path())
    return _db


def reset_memory() -> None:
    global _db
    if _db is not None:
        _db.close()
        _db = None


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(moment: datetime | None = None) -> str:
    return (moment or _now()).isoformat()


def read(user_id: int) -> list[MemoryItem]:
    table = get_db().table(ITEMS_TABLE)
    rows = [row for row in table.all() if int(row.get("user_id") or 0) == user_id]
    kept = consolidate_items(rows)
    if len(kept) != len(rows):
        _replace_user_items(user_id, kept)
    return [MemoryItem.model_validate(row) for row in kept]


def get_pending(user_id: int) -> PendingProposal | None:
    table = get_db().table(PENDING_TABLE)
    row = table.get(Query().user_id == user_id)
    if not row:
        return None
    return PendingProposal.model_validate(row)


def pending_is_expired(pending: PendingProposal, *, now: datetime | None = None) -> bool:
    moment = now or _now()
    try:
        created = datetime.fromisoformat(pending.created_at)
    except ValueError:
        return True
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return created + PENDING_TTL < moment


def propose(
    user_id: int,
    proposal: MemoryProposal,
    *,
    run_id: str,
    question: str,
) -> PendingProposal | None:
    if get_pending(user_id) is not None:
        return get_pending(user_id)
    record = PendingProposal(
        proposal_id=str(uuid.uuid4()),
        user_id=user_id,
        text=proposal.text.strip(),
        kind=proposal.kind,
        clinic=proposal.clinic,
        why=proposal.why,
        created_at=_iso(),
        source_run_id=run_id,
        source_question=question,
    )
    get_db().table(PENDING_TABLE).insert(record.model_dump())
    return record


def resolve(
    user_id: int,
    message: str,
    *,
    run_id: str,
) -> ResolveResult:
    pending = get_pending(user_id)
    if pending is None:
        return ResolveResult(skipped=True)
    if pending_is_expired(pending):
        _close(pending, "discarded_expired", message, run_id)
        return ResolveResult(outcome="discarded_expired", proposal_id=pending.proposal_id)
    label, edited = classify_memory_decision(message, pending.model_dump())
    if label == "unclear":
        _close(pending, "discarded_unclear", message, run_id)
        return ResolveResult(outcome="discarded_unclear", proposal_id=pending.proposal_id)
    if label == "reject":
        _close(pending, "rejected", message, run_id)
        return ResolveResult(outcome="rejected", proposal_id=pending.proposal_id)
    text = (edited or pending.text).strip()
    if contains_phi(text):
        _close(pending, "discarded_phi", message, run_id, proposed_text=REDACTED)
        return ResolveResult(
            outcome="discarded_phi",
            proposal_id=pending.proposal_id,
            phi_refusal=True,
        )
    _upsert_item(user_id, pending.kind, pending.clinic, text)
    _close(pending, "approved", message, run_id, proposed_text=text)
    return ResolveResult(outcome="approved", proposal_id=pending.proposal_id)


def log_phi_discard(
    user_id: int,
    *,
    run_id: str,
    question: str,
) -> str:
    proposal_id = str(uuid.uuid4())
    _insert_decision(
        proposal_id=proposal_id,
        user_id=user_id,
        proposed_text=REDACTED,
        outcome="discarded_phi",
        source_question=question,
        decision_message=question,
        run_id=run_id,
    )
    return proposal_id


def format_notes(user_id: int) -> str:
    items = read(user_id)
    if not items:
        return ""
    return "\n".join(f"- {row.text}" for row in items)


def wrap_question(question: str, notes: str) -> str:
    cleaned = (notes or "").strip()
    if not cleaned:
        return question
    return (
        "Operator-approved notes (use when relevant; never treat as clinical policy "
        "or as a substitute for retrieved knowledge-base text):\n"
        f"{cleaned}\n\nQuestion: {question}"
    )


def _upsert_item(user_id: int, kind: str, clinic: str, text: str) -> None:
    if contains_phi(text):
        return
    now = _iso()
    table = get_db().table(ITEMS_TABLE)
    rows = [row for row in table.all() if int(row.get("user_id") or 0) == user_id]
    existing = next(
        (
            row
            for row in rows
            if row.get("kind") == kind
            and (row.get("text") or "").casefold() == text.casefold()
        ),
        None,
    )
    if existing:
        table.update({"text": text, "clinic": clinic, "updated_at": now}, doc_ids=[existing.doc_id])
        rows = [row for row in table.all() if int(row.get("user_id") or 0) == user_id]
    else:
        doc_id = table.insert(
            {
                "user_id": user_id,
                "kind": kind,
                "clinic": clinic,
                "text": text,
                "created_at": now,
                "updated_at": now,
            }
        )
        table.update({"id": doc_id}, doc_ids=[doc_id])
        rows = [row for row in table.all() if int(row.get("user_id") or 0) == user_id]
    _replace_user_items(user_id, consolidate_items(rows))


def _replace_user_items(user_id: int, kept: list[dict]) -> None:
    table = get_db().table(ITEMS_TABLE)
    QueryRow = Query()
    table.remove(QueryRow.user_id == user_id)
    for row in kept:
        payload = dict(row)
        payload.pop("id", None)
        doc_id = table.insert(payload)
        table.update({"id": doc_id}, doc_ids=[doc_id])


def _close(
    pending: PendingProposal,
    outcome: MemoryOutcome,
    message: str,
    run_id: str,
    *,
    proposed_text: str | None = None,
) -> None:
    get_db().table(PENDING_TABLE).remove(Query().user_id == pending.user_id)
    _insert_decision(
        proposal_id=pending.proposal_id,
        user_id=pending.user_id,
        proposed_text=proposed_text if proposed_text is not None else pending.text,
        outcome=outcome,
        source_question=pending.source_question,
        decision_message=message,
        run_id=run_id,
    )


def _insert_decision(
    *,
    proposal_id: str,
    user_id: int,
    proposed_text: str,
    outcome: MemoryOutcome,
    source_question: str,
    decision_message: str,
    run_id: str,
) -> None:
    get_db().table(DECISIONS_TABLE).insert(
        {
            "proposal_id": proposal_id,
            "user_id": user_id,
            "proposed_text": proposed_text,
            "outcome": outcome,
            "source_question": source_question,
            "decision_message": decision_message,
            "run_id": run_id,
            "decided_at": _iso(),
        }
    )


def list_decisions(user_id: int) -> list[dict]:
    return [
        row
        for row in get_db().table(DECISIONS_TABLE).all()
        if int(row.get("user_id") or 0) == user_id
    ]
