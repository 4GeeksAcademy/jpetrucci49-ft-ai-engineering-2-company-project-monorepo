"""SQLModel writes for RFP drafts. Never persist PHI spans; never discard on eval fail."""

from __future__ import annotations

import logging
from typing import Any

from sqlmodel import Session, select

from agent.memory.phi import contains_phi
from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS
from rfp.models import RfpDepartmentSection, RfpTicket, utc_now

logger = logging.getLogger(__name__)

PHI_BLOCKED = "Content blocked pending Compliance review."
DRAFT_PIPELINE_ERROR = "draft_pipeline_error"


def _open_session() -> Session:
    from inventory.database import get_session_factory

    return get_session_factory()()


def load_handoff(ticket_id: str) -> dict[str, Any]:
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")
        if not ticket.handoff_json:
            raise ValueError(f"ticket {ticket_id} has no handoff_json")
        return dict(ticket.handoff_json)
    finally:
        session.close()


def persist_status(ticket_id: str, status: str) -> None:
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")
        ticket.status = status
        ticket.updated_at = utc_now()
        session.add(ticket)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def persist_draft_pipeline_error(ticket_id: str) -> None:
    """Crash mid-Part-2: leave drafting/under_evaluation; never discarded."""
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            return
        if ticket.status not in {"drafting", "under_evaluation"}:
            ticket.status = "drafting"
        ticket.error_code = DRAFT_PIPELINE_ERROR
        ticket.updated_at = utc_now()
        session.add(ticket)
        session.commit()
    except Exception:
        logger.exception("failed to mark draft_pipeline_error for ticket")
        session.rollback()
    finally:
        session.close()


def persist_drafts(
    ticket_id: str,
    *,
    drafts: dict[str, str],
    results: dict[str, Any],
) -> dict[str, Any]:
    session = _open_session()
    try:
        ticket = session.get(RfpTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"unknown ticket {ticket_id}")

        departments: list[dict[str, Any]] = []
        any_provisional = False
        for dept, owner in DEPARTMENT_OWNERS.items():
            raw_draft = drafts.get(dept) or ""
            evaluation = dict(results.get(dept) or {})
            if contains_phi(raw_draft):
                stored_draft = PHI_BLOCKED
                compliance = dict(evaluation.get("compliance") or {})
                compliance["pass"] = False
                compliance["contains_phi"] = True
                rules = list(compliance.get("rule_ids") or [])
                if "no-phi" not in rules:
                    rules.append("no-phi")
                compliance["rule_ids"] = rules
                violations = list(compliance.get("violations") or [])
                if "Draft contains patient identifiers or diagnosis language." not in violations:
                    violations.append("Draft contains patient identifiers or diagnosis language.")
                compliance["violations"] = violations
                evaluation["compliance"] = compliance
                evaluation["overall_pass"] = False
                evaluation["feedback_for_generator"] = (
                    "Fix compliance no-phi: remove patient identifiers and diagnosis language."
                )
            else:
                stored_draft = raw_draft
            needs_review = bool(evaluation.get("needs_human_review"))
            any_provisional = any_provisional or needs_review

            row = session.exec(
                select(RfpDepartmentSection).where(
                    RfpDepartmentSection.ticket_id == ticket_id,
                    RfpDepartmentSection.department_id == dept,
                )
            ).first()
            if row is None:
                row = RfpDepartmentSection(
                    ticket_id=ticket_id,
                    department_id=dept,
                    key_aspects=[],
                    open_questions=[],
                )
            row.draft_content = stored_draft
            row.evaluation_results = evaluation
            session.add(row)
            departments.append(
                {
                    "department_id": dept,
                    "owner": owner,
                    "draft_content": stored_draft,
                    "evaluation_results": evaluation,
                    "needs_human_review": needs_review,
                }
            )

        ticket_status = "needs_human_review" if any_provisional else "under_evaluation"
        ticket.status = ticket_status
        ticket.error_code = None
        ticket.part2_handoff_json = {
            "ticket_id": ticket_id,
            "ticket_status": ticket_status,
            "departments": departments,
        }
        ticket.updated_at = utc_now()
        session.add(ticket)
        session.commit()
        return dict(ticket.part2_handoff_json)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
