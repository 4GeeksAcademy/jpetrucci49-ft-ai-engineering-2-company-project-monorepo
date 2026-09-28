"""Desk-agent durable memory: TinyDB items + pending + decisions. Not RAG."""

from __future__ import annotations

from agent.memory.phi import PHI_REFUSAL, contains_phi
from agent.memory.store import (
    MemoryItem,
    MemoryProposal,
    PendingProposal,
    ResolveResult,
    format_notes,
    get_pending,
    log_phi_discard,
    propose,
    read,
    reset_memory,
    resolve,
    wrap_question,
)


class AgentMemory:
    """Explicit read / propose / resolve surface. Does not grow a messages list."""

    def read(self, user_id: int) -> list[MemoryItem]:
        return read(user_id)

    def propose(
        self,
        user_id: int,
        proposal: MemoryProposal,
        *,
        run_id: str,
        question: str,
    ) -> PendingProposal | None:
        return propose(user_id, proposal, run_id=run_id, question=question)

    def resolve(self, user_id: int, message: str, *, run_id: str) -> ResolveResult:
        return resolve(user_id, message, run_id=run_id)


def get_memory() -> AgentMemory:
    return AgentMemory()


__all__ = [
    "AgentMemory",
    "MemoryItem",
    "MemoryProposal",
    "PHI_REFUSAL",
    "PendingProposal",
    "ResolveResult",
    "contains_phi",
    "format_notes",
    "get_memory",
    "get_pending",
    "log_phi_discard",
    "propose",
    "read",
    "reset_memory",
    "resolve",
    "wrap_question",
]
