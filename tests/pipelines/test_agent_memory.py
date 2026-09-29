"""Desk-agent memory: propose → confirm → consolidate. Isolated TinyDB, mocked RAG."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agent.graph import run_desk_agent
from agent.memory.classify import classify_memory_decision
from agent.memory.consolidate import ITEM_CAP, consolidate_items
from agent.memory.phi import PHI_REFUSAL, contains_phi
from agent.memory.propose import REMEMBER_PROMPT, should_propose
from agent.memory.store import (
    MemoryProposal,
    format_notes,
    get_pending,
    list_decisions,
    propose,
    read,
    reset_memory,
    resolve,
    wrap_question,
)
from agent.traces import traces_dir
from data.pipelines.rag import NO_INFORMATION

MANCHESTER = (
    "At the Manchester clinic, internal referrals now go through the coordinator "
    "before the specialist — that changed last quarter."
)
AUSTIN = (
    "That high no-show alert at the Austin clinic was because of a road closure "
    "that week, not a real problem with the reminder programme."
)
DIANE = (
    "The weekly report for Diane Foster needs vacancies broken down by role, "
    "not just by clinic — she asked for that two weeks ago."
)
NO_SHOW = "What's this week's no-show rate?"
PHI_JOHNSON = "Patient Johnson cancelled tomorrow's appointment, note that down."
THANKS = "Thanks, that settles my report."
POLICY = "Is there a charge for cancelling 12 hours in advance?"


@pytest.fixture(autouse=True)
def _isolate_agent_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(tmp_path / "agent_memory.json"))
    reset_memory()
    yield
    reset_memory()


def _mock_rag(monkeypatch: pytest.MonkeyPatch, answer: str = "Policy answer.") -> list[str]:
    seen: list[str] = []
    monkeypatch.setattr(
        "agent.nodes.retrieve",
        lambda question, k=5: [
            {
                "source_document": "appointment-policy",
                "section": "Cancellation policy",
                "text": "Cancelling less than 24 hours in advance: 50 USD.",
            }
        ],
    )

    def _generate(question: str, context: list) -> str:
        del context
        seen.append(question)
        return answer

    monkeypatch.setattr("agent.nodes.generate_answer", _generate)
    return seen


def _cleanup(run_id: str) -> None:
    (traces_dir() / f"{run_id}.json").unlink(missing_ok=True)


def test_memory_not_always(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_rag(monkeypatch)
    user_id = 11
    for question in (NO_SHOW, THANKS, POLICY):
        run_id = f"a1111111-1111-4111-8111-{user_id:012d}"
        result = run_desk_agent(question, user_id=user_id, run_id=run_id)
        assert get_pending(user_id) is None
        assert read(user_id) == []
        assert REMEMBER_PROMPT not in (result.get("answer") or "")
        _cleanup(run_id)
        user_id += 1


def test_memory_phi_rejected_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent.nodes.retrieve", lambda *_a, **_k: [])
    user_id = 21
    run_id = "b2222222-2222-4222-8222-000000000021"
    result = run_desk_agent(PHI_JOHNSON, user_id=user_id, run_id=run_id)
    answer = result.get("answer") or ""
    assert PHI_REFUSAL in answer
    assert "can't remember" in answer.lower() or "cannot store" in answer.lower()
    assert get_pending(user_id) is None
    assert read(user_id) == []
    rows = list_decisions(user_id)
    assert any(row.get("outcome") == "discarded_phi" for row in rows)
    assert all(row.get("proposed_text") != PHI_JOHNSON for row in rows)
    assert any(row.get("proposed_text") == "[redacted]" for row in rows)
    _cleanup(run_id)


def test_memory_one_pending() -> None:
    user_id = 31
    first = propose(
        user_id,
        MemoryProposal(text="Manchester referrals go through the coordinator", kind="clinic_protocol", clinic="Manchester"),
        run_id="c3333333-3333-4333-8333-000000000031",
        question=MANCHESTER,
    )
    second = propose(
        user_id,
        MemoryProposal(text="Austin road closure", kind="incident_pattern", clinic="Austin"),
        run_id="c3333333-3333-4333-8333-000000000032",
        question=AUSTIN,
    )
    assert first is not None and second is not None
    assert first.proposal_id == second.proposal_id
    assert get_pending(user_id) is not None
    assert read(user_id) == []


def test_memory_unclear_discards(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_rag(monkeypatch)
    user_id = 41
    first_id = "d4444444-4444-4444-8444-000000000041"
    run_desk_agent(MANCHESTER, user_id=user_id, run_id=first_id)
    pending = get_pending(user_id)
    assert pending is not None
    second_id = "d4444444-4444-4444-8444-000000000042"
    run_desk_agent(POLICY, user_id=user_id, run_id=second_id)
    assert get_pending(user_id) is None
    assert read(user_id) == []
    rows = list_decisions(user_id)
    assert any(row.get("outcome") == "discarded_unclear" for row in rows)
    _cleanup(first_id)
    _cleanup(second_id)


def test_memory_approve_then_used(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _mock_rag(monkeypatch)
    user_id = 51
    propose_id = "e5555555-5555-4555-8555-000000000051"
    result = run_desk_agent(MANCHESTER, user_id=user_id, run_id=propose_id)
    assert REMEMBER_PROMPT in (result.get("answer") or "")
    assert get_pending(user_id) is not None
    yes_id = "e5555555-5555-4555-8555-000000000052"
    run_desk_agent("yes", user_id=user_id, run_id=yes_id)
    items = read(user_id)
    assert len(items) == 1
    assert "Manchester" in items[0].text or "coordinator" in items[0].text.casefold()
    assert get_pending(user_id) is None
    use_id = "e5555555-5555-4555-8555-000000000053"
    run_desk_agent(POLICY, user_id=user_id, run_id=use_id)
    assert seen[-1].startswith("Operator-approved notes")
    assert "manchester" in seen[-1].casefold() or "coordinator" in seen[-1].casefold()
    assert wrap_question(POLICY, format_notes(user_id)).startswith("Operator-approved notes")
    _cleanup(propose_id)
    _cleanup(yes_id)
    _cleanup(use_id)


def test_memory_reject_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_rag(monkeypatch)
    user_id = 61
    propose_id = "f6666666-6666-4666-8666-000000000061"
    run_desk_agent(AUSTIN, user_id=user_id, run_id=propose_id)
    assert get_pending(user_id) is not None
    reject_id = "f6666666-6666-4666-8666-000000000062"
    run_desk_agent("no", user_id=user_id, run_id=reject_id)
    assert read(user_id) == []
    assert get_pending(user_id) is None
    rows = list_decisions(user_id)
    assert any(row.get("outcome") == "rejected" for row in rows)
    later_id = "f6666666-6666-4666-8666-000000000063"
    later = run_desk_agent(POLICY, user_id=user_id, run_id=later_id)
    assert "road closure" not in (later.get("answer") or "").casefold()
    _cleanup(propose_id)
    _cleanup(reject_id)
    _cleanup(later_id)


def test_agent_no_qdrant_memory() -> None:
    root = Path(__file__).resolve().parents[2] / "services" / "api" / "agent" / "memory"
    blob = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "healthcore_knowledge" not in blob
    assert "qdrant" not in blob.casefold()
    assert "embed(" not in blob
    assert "setup(" not in blob


def test_classifier_does_not_treat_yesterday_as_yes() -> None:
    assert classify_memory_decision("yesterday", {}) == ("unclear", None)
    assert classify_memory_decision("yes", {}) == ("approve", None)
    assert classify_memory_decision("no", {}) == ("reject", None)
    label, edited = classify_memory_decision(
        "remember this instead: Manchester uses the deputy coordinator",
        {},
    )
    assert label == "edit"
    assert edited is not None and "deputy" in edited


def test_phi_covers_us_and_uk_identifiers() -> None:
    assert contains_phi("Patient Johnson cancelled")
    assert contains_phi("NHS number 123 456 7890")
    assert contains_phi("MRN: 998877")
    assert not contains_phi(MANCHESTER)
    assert not contains_phi(DIANE)


def test_should_propose_context_examples() -> None:
    assert should_propose(MANCHESTER, "") is not None
    assert should_propose(AUSTIN, "") is not None
    assert should_propose(DIANE, "") is not None
    assert should_propose(NO_SHOW, "") is None
    assert should_propose(PHI_JOHNSON, "") is None
    assert should_propose(THANKS, "") is None


def test_expired_pending_does_not_approve() -> None:
    user_id = 71
    pending = propose(
        user_id,
        MemoryProposal(text="Harborview uses the night coordinator", kind="clinic_protocol", clinic="Harborview"),
        run_id="aa777777-7777-4777-8777-000000000071",
        question="Remember that Harborview uses the night coordinator",
    )
    assert pending is not None
    from tinydb import Query

    from agent.memory.store import get_db

    get_db().table("pending").update(
        {"created_at": (datetime.now(UTC) - timedelta(hours=25)).isoformat()},
        Query().user_id == user_id,
    )
    result = resolve(user_id, "yes", run_id="aa777777-7777-4777-8777-000000000072")
    assert result.outcome == "discarded_expired"
    assert read(user_id) == []


def test_consolidate_caps_and_dedupes() -> None:
    now = datetime.now(UTC)
    rows = [
        {
            "user_id": 1,
            "kind": "clinic_protocol",
            "clinic": "Austin",
            "text": f"note {index}",
            "updated_at": (now - timedelta(days=index)).isoformat(),
        }
        for index in range(ITEM_CAP + 5)
    ]
    rows.append(
        {
            "user_id": 1,
            "kind": "clinic_protocol",
            "clinic": "Austin",
            "text": "note 0",
            "updated_at": now.isoformat(),
        }
    )
    kept = consolidate_items(rows, now=now)
    assert len(kept) <= ITEM_CAP
    texts = [row["text"] for row in kept]
    assert texts.count("note 0") == 1


def test_refuse_path_still_mentions_no_information(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent.nodes.retrieve", lambda *_a, **_k: [])
    run_id = "ab888888-8888-4888-8888-000000000081"
    result = run_desk_agent("What is the weather in Austin tomorrow?", user_id=81, run_id=run_id)
    assert result["answer"] == NO_INFORMATION
    assert get_pending(81) is None
    _cleanup(run_id)
