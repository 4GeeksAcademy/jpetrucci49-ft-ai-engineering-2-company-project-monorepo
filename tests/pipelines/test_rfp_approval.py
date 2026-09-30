"""Department approval interrupts, arbitration, and final document (no live LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, select

from data.pipelines.rfp_approval.decisions import ApprovalBlocked
from data.pipelines.rfp_approval.graph import (
    branch_waiting,
    reset_checkpointer,
    resume_approval,
    start_approvals,
)
from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS
from inventory.database import configure_engine, reset_engine
from rfp.models import RfpDepartmentSection, RfpTicket

CLEAN_DRAFTS = {
    "revenue": (
        "Revenue Cycle draft for Meridian Manufacturing. Commercial terms are quoted in USD. "
        "Fee tables stay an open question. No additional site count is stated."
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


@pytest.fixture()
def approval_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_engine()
    engine = configure_engine(f"sqlite:///{tmp_path / 'rfp_approval.db'}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setenv("RFP_APPROVAL_TRACE_DIR", str(tmp_path / "traces"))
    reset_checkpointer(str(tmp_path / "approval.sqlite"))
    yield engine
    reset_checkpointer()
    reset_engine()


def _eval() -> dict:
    return {
        "compliance": {"pass": True, "rule_ids": [], "violations": [], "contains_phi": False},
        "overall_pass": True,
        "needs_human_review": False,
        "iteration": 1,
    }


def _seed(
    engine,
    ticket_id: str,
    drafts: dict[str, str],
    *,
    population: int = 800,
    aspects: dict[str, list[str]] | None = None,
) -> None:
    aspects = aspects or {dept: ["Occupational health services."] for dept in DEPARTMENT_OWNERS}
    handoff = {
        "ticket_id": ticket_id,
        "phi_detected": False,
        "metadata": {
            "client_name": "Meridian Manufacturing",
            "client_country": "US",
            "program_type": "occupational_health",
            "covered_population": population,
            "currency": "USD",
        },
        "departments": [
            {
                "department_id": dept,
                "owner": owner,
                "key_aspects": aspects.get(dept, []),
                "open_questions": [],
            }
            for dept, owner in DEPARTMENT_OWNERS.items()
        ],
        "synthesizer_summary": "Ask each owner to review their section.",
    }
    part2 = {
        "ticket_id": ticket_id,
        "ticket_status": "under_evaluation",
        "departments": [
            {
                "department_id": dept,
                "owner": owner,
                "draft_content": drafts[dept],
                "evaluation_results": _eval(),
                "needs_human_review": False,
            }
            for dept, owner in DEPARTMENT_OWNERS.items()
        ],
    }
    with Session(engine) as session:
        session.add(
            RfpTicket(
                ticket_id=ticket_id,
                status="under_evaluation",
                raw_pdf_path=str(tmp_pdf_placeholder(engine, ticket_id)),
                created_by="1",
                handoff_json=handoff,
                part2_handoff_json=part2,
            )
        )
        session.flush()
        for dept, owner in DEPARTMENT_OWNERS.items():
            session.add(
                RfpDepartmentSection(
                    ticket_id=ticket_id,
                    department_id=dept,
                    key_aspects=aspects.get(dept, []),
                    open_questions=[],
                    draft_content=drafts[dept],
                    evaluation_results=_eval(),
                )
            )
        session.commit()


def tmp_pdf_placeholder(engine, ticket_id: str) -> Path:
    path = Path(engine.url.database).parent / f"{ticket_id}.pdf"
    path.write_bytes(b"%PDF-1.1\n%%EOF\n")
    return path


def _section(engine, ticket_id: str, department_id: str) -> RfpDepartmentSection:
    with Session(engine) as session:
        row = session.exec(
            select(RfpDepartmentSection).where(
                RfpDepartmentSection.ticket_id == ticket_id,
                RfpDepartmentSection.department_id == department_id,
            )
        ).one()
        session.expunge(row)
        return row


def _ticket(engine, ticket_id: str) -> RfpTicket:
    with Session(engine) as session:
        row = session.get(RfpTicket, ticket_id)
        assert row is not None
        session.expunge(row)
        return row


def _trace(tmp_path: Path, ticket_id: str) -> list[dict]:
    return json.loads((tmp_path / "traces" / f"{ticket_id}.json").read_text(encoding="utf-8"))


def test_interrupt_resume_sets_owner_from_checkpoint(approval_db, tmp_path: Path) -> None:
    ticket_id = "approve-compliance"
    _seed(approval_db, ticket_id, CLEAN_DRAFTS)
    start_approvals(ticket_id)
    assert branch_waiting(ticket_id, "compliance")
    resume_approval(ticket_id, "compliance", "approve", None)
    row = _section(approval_db, ticket_id, "compliance")
    assert row.approval_status == "approved"
    assert row.approver == "Claire Whitfield"
    assert row.approved_at is not None
    resume_approval(ticket_id, "revenue", "approve", None, approver="Alex Rivera")
    assert _section(approval_db, ticket_id, "revenue").approver == "Alex Rivera"
    events = _trace(tmp_path, ticket_id)
    interrupt_at = next(index for index, item in enumerate(events) if item["node"] == "interrupt_approval")
    resume_at = next(index for index, item in enumerate(events) if item["node"] == "resume_approval")
    assert interrupt_at < resume_at


def test_resume_clinical_leaves_revenue_interrupted(approval_db) -> None:
    ticket_id = "parallel-branches"
    _seed(approval_db, ticket_id, CLEAN_DRAFTS)
    start_approvals(ticket_id)
    resume_approval(ticket_id, "clinical", "approve", None)
    assert _section(approval_db, ticket_id, "clinical").approver == "Dr. Marcus Reid"
    assert branch_waiting(ticket_id, "revenue")
    assert _section(approval_db, ticket_id, "revenue").approval_status is None
    assert _ticket(approval_db, ticket_id).status == "waiting_for_approval"
    assert _ticket(approval_db, ticket_id).final_document_json is None


def test_request_changes_saves_edited_proposal_and_comment(approval_db) -> None:
    ticket_id = "edited-draft"
    _seed(approval_db, ticket_id, CLEAN_DRAFTS)
    start_approvals(ticket_id)
    revised = "Revenue proposal revised by the manager for Meridian Manufacturing in USD."
    resume_approval(
        ticket_id,
        "revenue",
        "request_changes",
        "Use this wording.",
        draft_content=revised,
    )
    row = _section(approval_db, ticket_id, "revenue")
    assert row.draft_content == revised
    assert row.approval_status == "changes_requested"
    recorded = (row.evaluation_results or {}).get("last_decision") or {}
    assert recorded["comment"] == "Use this wording."
    assert recorded["capped"] is False
    assert _ticket(approval_db, ticket_id).status == "waiting_for_approval"


def test_third_request_changes_caps(approval_db, tmp_path: Path) -> None:
    ticket_id = "iteration-cap"
    _seed(approval_db, ticket_id, CLEAN_DRAFTS)
    start_approvals(ticket_id)
    for _ in range(3):
        resume_approval(ticket_id, "revenue", "request_changes", "Restate the USD terms.")
    row = _section(approval_db, ticket_id, "revenue")
    assert row.approval_status != "approved"
    assert row.approver is None
    assert _ticket(approval_db, ticket_id).status == "waiting_for_approval"
    assert any(item["output_summary"] == "approval_iteration_cap" for item in _trace(tmp_path, ticket_id))


def test_us_compliance_without_baa_blocks_approve(approval_db) -> None:
    ticket_id = "baa-block"
    drafts = {
        **CLEAN_DRAFTS,
        "compliance": (
            "Compliance review for Meridian Manufacturing in the United States. "
            "The section discusses records retention and staff training only."
        ),
    }
    _seed(approval_db, ticket_id, drafts)
    start_approvals(ticket_id)
    row = _section(approval_db, ticket_id, "compliance")
    records = (row.evaluation_results or {}).get("arbitration") or []
    assert records[0]["trigger_id"] == "baa-dpa-mismatch"
    assert records[0]["arbiter"] == "Claire Whitfield"
    with pytest.raises(ApprovalBlocked) as caught:
        resume_approval(ticket_id, "compliance", "approve", None)
    assert caught.value.trigger_id == "baa-dpa-mismatch"
    assert branch_waiting(ticket_id, "compliance")
    assert _ticket(approval_db, ticket_id).final_document_json is None


def test_capacity_below_population_blocks_clinical_and_revenue(approval_db) -> None:
    ticket_id = "capacity-block"
    drafts = {
        **CLEAN_DRAFTS,
        "clinical": "Operations review. staff capacity stated as 2 for the programme.",
    }
    _seed(approval_db, ticket_id, drafts, population=800)
    start_approvals(ticket_id)
    for dept in ("clinical", "revenue"):
        row = _section(approval_db, ticket_id, dept)
        records = (row.evaluation_results or {}).get("arbitration") or []
        match = next(item for item in records if item["trigger_id"] == "capacity-vs-population")
        assert match["arbiter"] == "Tom Callahan"
        assert match["action"] == "request_changes"
        assert match["affected_departments"] == ["clinical", "revenue"]
    compliance = _section(approval_db, ticket_id, "compliance")
    assert "capacity-vs-population" not in {
        item["trigger_id"] for item in (compliance.evaluation_results or {}).get("arbitration") or []
    }


def test_three_approves_write_usd_final_document(approval_db) -> None:
    ticket_id = "final-doc"
    _seed(approval_db, ticket_id, CLEAN_DRAFTS)
    start_approvals(ticket_id)
    for dept in DEPARTMENT_OWNERS:
        resume_approval(ticket_id, dept, "approve", None)
    ticket = _ticket(approval_db, ticket_id)
    assert ticket.status == "done"
    document = ticket.final_document_json or {}
    assert document["currency"] == "USD"
    assert [section["department_id"] for section in document["sections"]] == [
        "revenue",
        "clinical",
        "compliance",
    ]
    assert document["sections"][0]["approver"] == "Tom Callahan"
    assert document["sections"][2]["approver"] == "Claire Whitfield"
