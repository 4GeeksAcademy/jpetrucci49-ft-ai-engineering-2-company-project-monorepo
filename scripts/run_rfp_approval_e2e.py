#!/usr/bin/env python3
"""Seed or reuse a Part 2 handoff, approve all three departments, exit 0 only when done."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"
for path in (REPO_ROOT, API_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sqlmodel import Session  # noqa: E402

from data.pipelines.rfp_approval.graph import resume_approval, start_approvals  # noqa: E402
from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS  # noqa: E402
from inventory.database import get_session_factory, init_inventory_schema  # noqa: E402
from rfp.models import RfpDepartmentSection, RfpTicket  # noqa: E402

CLEAN_DRAFTS = {
    "revenue": (
        "Revenue Cycle draft for Meridian Manufacturing. Commercial terms are quoted in USD. "
        "Fee tables stay an open question."
    ),
    "clinical": (
        "Clinical Operations draft for Meridian Manufacturing. On-site occupational health "
        "scheduling is described without a numeric headcount."
    ),
    "compliance": (
        "Compliance review for Meridian Manufacturing in the United States. "
        "This section includes a Business Associate Agreement (BAA)."
    ),
}


def _seed(ticket_id: str) -> None:
    handoff = {
        "ticket_id": ticket_id,
        "phi_detected": False,
        "metadata": {
            "client_name": "Meridian Manufacturing",
            "client_country": "US",
            "program_type": "occupational_health",
            "covered_population": 800,
            "currency": "USD",
        },
        "departments": [
            {
                "department_id": dept,
                "owner": owner,
                "key_aspects": ["Occupational health services."],
                "open_questions": [],
            }
            for dept, owner in DEPARTMENT_OWNERS.items()
        ],
    }
    part2 = {
        "ticket_id": ticket_id,
        "ticket_status": "under_evaluation",
        "departments": [
            {
                "department_id": dept,
                "owner": owner,
                "draft_content": CLEAN_DRAFTS[dept],
                "evaluation_results": {
                    "compliance": {"pass": True, "rule_ids": [], "contains_phi": False},
                    "overall_pass": True,
                },
                "needs_human_review": False,
            }
            for dept, owner in DEPARTMENT_OWNERS.items()
        ],
    }
    session = get_session_factory()()
    try:
        session.add(
            RfpTicket(
                ticket_id=ticket_id,
                status="under_evaluation",
                raw_pdf_path=str(REPO_ROOT / "data" / "raw" / "rfp" / f"{ticket_id}.pdf"),
                created_by="e2e",
                handoff_json=handoff,
                part2_handoff_json=part2,
            )
        )
        session.flush()
        for dept in DEPARTMENT_OWNERS:
            session.add(
                RfpDepartmentSection(
                    ticket_id=ticket_id,
                    department_id=dept,
                    key_aspects=["Occupational health services."],
                    open_questions=[],
                    draft_content=CLEAN_DRAFTS[dept],
                    evaluation_results={"compliance": {"contains_phi": False, "pass": True, "rule_ids": []}},
                )
            )
        session.commit()
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve a seeded RFP and require status done.")
    parser.add_argument("--ticket-id", default="", help="Existing ticket with a Part 2 handoff")
    args = parser.parse_args()
    init_inventory_schema()
    ticket_id = args.ticket_id.strip() or str(uuid4())
    if not args.ticket_id.strip():
        _seed(ticket_id)
    start_approvals(ticket_id)
    for dept in DEPARTMENT_OWNERS:
        resume_approval(ticket_id, dept, "approve", None)
    session: Session = get_session_factory()()
    try:
        ticket = session.get(RfpTicket, ticket_id)
    finally:
        session.close()
    status = ticket.status if ticket is not None else "missing"
    print(f"ticket_id={ticket_id} status={status}")
    return 0 if status == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
