"""RFP draft generators, evaluators, and persist (no live LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, select

from data.pipelines.rfp_draft.evaluate import combine_evaluation, evaluate_compliance, evaluate_relevance
from data.pipelines.rfp_draft.generate import generate_section
from data.pipelines.rfp_draft.graph import GRAPH_NODES, run_rfp_draft
from data.pipelines.rfp_intake.workers import DEPARTMENT_OWNERS
from inventory.database import configure_engine, reset_engine
from rfp.models import RfpDepartmentSection, RfpTicket

MERIDIAN_HANDOFF = {
    "ticket_id": "meridian-draft",
    "phi_detected": False,
    "metadata": {
        "client_name": "Meridian Manufacturing",
        "client_country": "US",
        "program_type": "occupational_health",
        "covered_population": 800,
        "deadline": None,
        "budget_range": None,
        "currency": "USD",
    },
    "departments": [
        {
            "department_id": "revenue",
            "owner": "Tom Callahan",
            "key_aspects": [
                "Quote currency is USD (from client country).",
                "Contract length stated as 12 months.",
                "Institutional client: Meridian Manufacturing.",
            ],
            "open_questions": ["What payment structure and invoicing terms apply?"],
        },
        {
            "department_id": "clinical",
            "owner": "Dr. Marcus Reid",
            "key_aspects": [
                "Covered population stated as 800.",
                "On-site occupational or wellness coverage is requested.",
            ],
            "open_questions": [],
        },
        {
            "department_id": "compliance",
            "owner": "Claire Whitfield",
            "key_aspects": [
                "US client requires a Business Associate Agreement (BAA) under HIPAA.",
            ],
            "open_questions": [],
        },
    ],
    "synthesizer_summary": "Ask Tom Callahan about payment terms.",
}

THAMES_HANDOFF = {
    "ticket_id": "thames-draft",
    "phi_detected": False,
    "metadata": {
        "client_name": "Thames Valley University",
        "client_country": "UK",
        "program_type": "referral_network",
        "covered_population": None,
        "deadline": None,
        "budget_range": None,
        "currency": "GBP",
    },
    "departments": [
        {
            "department_id": "revenue",
            "owner": "Tom Callahan",
            "key_aspects": ["Quote currency is GBP (from client country)."],
            "open_questions": ["What budget or fee structure should Revenue Cycle use?"],
        },
        {
            "department_id": "clinical",
            "owner": "Dr. Marcus Reid",
            "key_aspects": ["A satellite clinic in the United Kingdom is requested."],
            "open_questions": ["What covered population / headcount must Clinical Operations staff for?"],
        },
        {
            "department_id": "compliance",
            "owner": "Claire Whitfield",
            "key_aspects": ["UK client requires a DPA referencing UK GDPR."],
            "open_questions": [],
        },
    ],
    "synthesizer_summary": "Ask Claire Whitfield about the DPA.",
}


@pytest.fixture(autouse=True)
def skip_live_rag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("data.pipelines.rag.retrieve", lambda *_args, **_kwargs: [])


@pytest.fixture()
def rfp_db(tmp_path: Path):
    reset_engine()
    engine = configure_engine(f"sqlite:///{tmp_path / 'rfp_draft.db'}")
    SQLModel.metadata.create_all(engine)
    yield engine
    reset_engine()


def _seed_complete(engine, ticket_id: str, handoff: dict) -> None:
    pdf_path = Path(engine.url.database).parent / f"{ticket_id}.pdf"
    pdf_path.write_bytes(b"%PDF-1.1\n%%EOF\n")
    payload = {**handoff, "ticket_id": ticket_id}
    with Session(engine) as session:
        session.add(
            RfpTicket(
                ticket_id=ticket_id,
                status="intake_complete",
                raw_pdf_path=str(pdf_path),
                created_by="1",
                handoff_json=payload,
            )
        )
        session.flush()
        for dept, _owner in DEPARTMENT_OWNERS.items():
            row = next(item for item in payload["departments"] if item["department_id"] == dept)
            session.add(
                RfpDepartmentSection(
                    ticket_id=ticket_id,
                    department_id=dept,
                    key_aspects=list(row["key_aspects"]),
                    open_questions=list(row["open_questions"]),
                )
            )
        session.commit()


def test_revenue_generator_uses_handoff_only() -> None:
    draft = generate_section("revenue", MERIDIAN_HANDOFF)
    assert "USD" in draft
    assert "Meridian" in draft or "12" in draft
    assert "staffing plan" not in draft.lower()
    assert "GBP" not in draft
    assert generate_section("revenue", THAMES_HANDOFF).count("GBP") >= 1


def test_relevance_evaluator_fails_when_aspects_ignored() -> None:
    draft = (
        "This generic scheduling note discusses invoices, calendar holds, and "
        "meeting rooms only. No volume or clinic-delivery facts are restated."
    )
    relevance = evaluate_relevance(
        draft,
        ["Covered population stated as 800.", "On-site occupational or wellness coverage is requested."],
    )
    assert relevance["pass"] is False
    assert relevance["missing_aspects"]
    combined = combine_evaluation(
        "clinical",
        {
            "readability": {"pass": True, "score": {}, "details": ""},
            "relevance": relevance,
            "compliance": {"pass": True, "rule_ids": [], "violations": [], "contains_phi": False},
        },
        iteration=1,
    )
    assert combined["overall_pass"] is False
    assert combined["feedback_for_generator"]
    assert "please improve the draft" not in combined["feedback_for_generator"].lower()


def test_us_compliance_without_baa_fails() -> None:
    draft = (
        "Compliance review for Meridian Manufacturing in the United States. "
        "The section discusses records retention and staff training only."
    )
    result = evaluate_compliance(
        draft,
        department_id="compliance",
        metadata=MERIDIAN_HANDOFF["metadata"],
        key_aspects=["US client requires a Business Associate Agreement (BAA) under HIPAA."],
    )
    assert result["pass"] is False
    assert "baa-us" in result["rule_ids"]


def test_phi_draft_fails_no_phi_rule() -> None:
    draft = "The patient Jane was diagnosed last week and needs occupational screening."
    result = evaluate_compliance(
        draft,
        department_id="clinical",
        metadata=MERIDIAN_HANDOFF["metadata"],
        key_aspects=["Covered population stated as 800."],
    )
    assert result["contains_phi"] is True
    assert "no-phi" in result["rule_ids"]


def test_graph_persists_three_drafts_and_part2_handoff(rfp_db) -> None:
    assert "assign" in GRAPH_NODES
    assert "combine_eval" in GRAPH_NODES
    _seed_complete(rfp_db, "meridian-draft", MERIDIAN_HANDOFF)
    run_rfp_draft("meridian-draft")
    with Session(rfp_db) as session:
        ticket = session.get(RfpTicket, "meridian-draft")
        assert ticket is not None
        assert ticket.status in {"under_evaluation", "needs_human_review"}
        assert ticket.status != "discarded"
        assert ticket.handoff_json is not None
        assert ticket.part2_handoff_json is not None
        assert ticket.part2_handoff_json["ticket_id"] == "meridian-draft"
        depts = {row["department_id"] for row in ticket.part2_handoff_json["departments"]}
        assert depts == {"revenue", "clinical", "compliance"}
        rows = session.exec(
            select(RfpDepartmentSection).where(RfpDepartmentSection.ticket_id == "meridian-draft")
        ).all()
        assert {row.department_id for row in rows} == {"revenue", "clinical", "compliance"}
        for row in rows:
            assert row.draft_content
            assert row.evaluation_results
            assert row.approval_status is None
            assert "Jane" not in (row.draft_content or "")
