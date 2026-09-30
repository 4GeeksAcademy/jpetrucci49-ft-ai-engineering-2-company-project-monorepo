"""Human resume validation. Approve, request changes, or reject."""

from __future__ import annotations

MAX_APPROVAL_ITERATIONS = 3
DECISIONS = frozenset({"approve", "request_changes", "reject"})


class ApprovalBlocked(Exception):
    """Approve refused while a CONTEXT trigger still matches this section."""

    def __init__(self, trigger_id: str) -> None:
        self.trigger_id = trigger_id
        super().__init__(trigger_id)


class ApprovalNotWaiting(Exception):
    """Resume target is not sitting on an interrupt."""


class InvalidDecision(ValueError):
    pass


def parse_decision(decision: str, comment: str | None) -> dict[str, str]:
    kind = (decision or "").strip()
    note = (comment or "").strip()
    if kind not in DECISIONS:
        raise InvalidDecision("Decision must be approve, request_changes, or reject.")
    if kind in {"request_changes", "reject"} and not note:
        raise InvalidDecision("A comment is required to request changes or reject.")
    return {"decision": kind, "comment": note}
