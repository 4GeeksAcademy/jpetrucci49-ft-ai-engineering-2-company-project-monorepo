"""RFP intake classifier, workers, PHI redact, and persist (no live LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, select

from agent.memory.phi import contains_phi
from data.pipelines.rfp_intake.classify import classify_rfp, classify_rfp_fallback
from data.pipelines.rfp_intake.convert import convert_document
from data.pipelines.rfp_intake.extracts import extract_metadata
from data.pipelines.rfp_intake.graph import GRAPH_NODES, run_rfp_intake
from data.pipelines.rfp_intake.workers import run_worker, synthesize
from inventory.database import configure_engine, reset_engine
from rfp.models import RfpDepartmentSection, RfpTicket

FORMAL = """
# Request for Proposal
Client: Meridian Manufacturing
Austin, Texas, United States
800 employees require on-site occupational health and wellness for a 12-month contract.
"""

INFORMAL = """
From: Thames Valley University
We would like a referral network partnership with a satellite clinic in the United Kingdom.
Please reply with next steps for a DPA under UK GDPR.
"""

VENDOR = """
# Introducing CloudEHR
Buy our electronic health record system to replace your EHR.
Our software platform is the future of hospital documentation.
"""

PHI_RFP = """
# Occupational health RFP
Client: Acme Logistics
United States
Please review the attached note. The patient Jane was diagnosed last week.
"""

MINIMAL_PDF = b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@pytest.fixture(autouse=True)
def no_live_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "data.pipelines.rfp_intake.classify._llm_classify",
        lambda _markdown: None,
    )


@pytest.fixture()
def rfp_db(tmp_path: Path):
    reset_engine()
    engine = configure_engine(f"sqlite:///{tmp_path / 'rfp.db'}")
    SQLModel.metadata.create_all(engine)
    yield engine
    reset_engine()


def _seed_ticket(engine, ticket_id: str, pdf_bytes: bytes = MINIMAL_PDF) -> None:
    pdf_path = Path(engine.url.database).parent / f"{ticket_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)
    with Session(engine) as session:
        session.add(
            RfpTicket(
                ticket_id=ticket_id,
                status="analyzing",
                raw_pdf_path=str(pdf_path),
                created_by="1",
            )
        )
        session.commit()


def test_classifier_accepts_formal_meridian() -> None:
    verdict = classify_rfp(FORMAL)
    assert verdict["is_rfp"] is True
    meta = extract_metadata(FORMAL)
    assert meta["client_name"] == "Meridian Manufacturing"
    assert meta["client_country"] == "US"
    assert meta["program_type"] == "occupational_health"
    assert meta["covered_population"] == 800
    assert meta["currency"] == "USD"


def test_classifier_accepts_informal_thames() -> None:
    verdict = classify_rfp(INFORMAL)
    assert verdict["is_rfp"] is True
    meta = extract_metadata(INFORMAL)
    assert meta["client_name"] == "Thames Valley University"
    assert meta["client_country"] == "UK"
    assert meta["program_type"] == "referral_network"
    assert meta["currency"] == "GBP"


def test_classifier_rejects_ehr_vendor_pitch() -> None:
    verdict = classify_rfp_fallback(VENDOR)
    assert verdict["is_rfp"] is False
    workers = [
        run_worker(dept, extract_metadata(VENDOR), VENDOR)
        for dept in ("revenue", "clinical", "compliance")
    ]
    assert verdict["reason"]
    assert all(isinstance(item["key_aspects"], list) for item in workers)


def test_clinical_worker_missing_volume_does_not_invent() -> None:
    result = run_worker(
        "clinical",
        {"covered_population": None, "program_type": "occupational_health", "client_country": "US"},
        "On-site occupational health is requested. No headcount is listed.",
    )
    joined = " ".join(result["key_aspects"])
    assert result["open_questions"]
    assert not any(char.isdigit() for char in joined)
    assert "800" not in joined


def test_workers_cover_three_departments_and_compliance_instruments() -> None:
    formal_meta = extract_metadata(FORMAL)
    informal_meta = extract_metadata(INFORMAL)
    formal_compliance = run_worker("compliance", formal_meta, FORMAL)
    informal_compliance = run_worker("compliance", informal_meta, INFORMAL)
    assert any("BAA" in item for item in formal_compliance["key_aspects"])
    assert any("DPA" in item or "UK GDPR" in item for item in informal_compliance["key_aspects"])
    handoff = synthesize("ticket-1", formal_meta, {
        "revenue": run_worker("revenue", formal_meta, FORMAL),
        "clinical": run_worker("clinical", formal_meta, FORMAL),
        "compliance": formal_compliance,
    })
    assert {row["department_id"] for row in handoff["departments"]} == {
        "revenue",
        "clinical",
        "compliance",
    }
    assert "Tom Callahan" in handoff["synthesizer_summary"]
    assert "Dr. Marcus Reid" in handoff["synthesizer_summary"]
    assert "Claire Whitfield" in handoff["synthesizer_summary"]


def test_phi_redacted_before_worker_and_persist(rfp_db) -> None:
    converted = convert_document(ticket_id="phi-ticket", pdf_path="", markdown=PHI_RFP)
    assert converted["phi_detected"] is True
    assert "Jane" not in converted["markdown"]
    assert contains_phi(converted["markdown"]) is False
    worker = run_worker(
        "compliance",
        converted["metadata"],
        converted["markdown"],
        phi_detected=True,
    )
    for aspect in worker["key_aspects"] + worker["open_questions"]:
        assert contains_phi(aspect) is False
    assert any("review" in item.lower() for item in worker["key_aspects"])


def test_graph_discards_vendor_and_completes_formal(rfp_db) -> None:
    assert "classify" in GRAPH_NODES
    _seed_ticket(rfp_db, "vendor-1")
    run_rfp_intake("vendor-1", markdown=VENDOR)
    with Session(rfp_db) as session:
        ticket = session.get(RfpTicket, "vendor-1")
        assert ticket is not None
        assert ticket.status == "discarded"
        assert ticket.discard_reason == "not_an_rfp"
        sections = session.exec(
            select(RfpDepartmentSection).where(RfpDepartmentSection.ticket_id == "vendor-1")
        ).all()
        assert sections == []

    _seed_ticket(rfp_db, "formal-1")
    run_rfp_intake("formal-1", markdown=FORMAL)
    with Session(rfp_db) as session:
        ticket = session.get(RfpTicket, "formal-1")
        assert ticket is not None
        assert ticket.status == "intake_complete"
        assert ticket.handoff_json is not None
        assert ticket.handoff_json["ticket_id"] == "formal-1"
        depts = {row["department_id"] for row in ticket.handoff_json["departments"]}
        assert depts == {"revenue", "clinical", "compliance"}
        rows = session.exec(
            select(RfpDepartmentSection).where(RfpDepartmentSection.ticket_id == "formal-1")
        ).all()
        assert {row.department_id for row in rows} == {"revenue", "clinical", "compliance"}
        for row in rows:
            for aspect in row.key_aspects:
                assert contains_phi(aspect) is False
