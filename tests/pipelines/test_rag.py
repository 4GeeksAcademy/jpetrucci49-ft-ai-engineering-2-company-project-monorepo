"""Unit tests for HealthCore RAG retrieve/query. No live Qdrant or LLM."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from data.pipelines import rag as rag_pipeline


def _hit(score: float, text: str, source: str = "appointment-policy") -> SimpleNamespace:
    return SimpleNamespace(
        score=score,
        payload={
            "company": "healthcore",
            "source_document": source,
            "section": "Cancellation policy",
            "language": "en",
            "chunk_index": 1,
            "text": text,
        },
    )


class _FakeClient:
    def __init__(self, hits: list[SimpleNamespace]) -> None:
        self.hits = hits

    def search(self, **_: object) -> list[SimpleNamespace]:
        return self.hits

    def query_points(self, **_: object) -> SimpleNamespace:
        return SimpleNamespace(points=self.hits)


def test_retrieve_excludes_scores_below_min(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rag_pipeline, "embed", lambda _: [0.1, 0.2])
    client = _FakeClient(
        [
            _hit(0.91, "Cancelling more than 24 hours in advance: no charge."),
            _hit(0.12, "Unrelated low-score chunk."),
        ]
    )
    results = rag_pipeline.retrieve("cancel 12 hours", k=5, min_score=0.35, client=client)
    assert len(results) == 1
    assert results[0]["text"].startswith("Cancelling more than 24 hours")
    assert results[0]["score"] == 0.91
    assert all(row["score"] >= 0.35 for row in results)


def test_retrieve_can_return_fewer_than_k(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rag_pipeline, "embed", lambda _: [0.1, 0.2])
    client = _FakeClient(
        [
            _hit(0.8, "Medicare or Medicaid patients: not charged a no-show fee."),
            _hit(0.2, "Below threshold."),
        ]
    )
    results = rag_pipeline.retrieve("medicare no-show", k=5, min_score=0.35, client=client)
    assert len(results) < 5
    assert len(results) == 1


def test_query_returns_model_output_not_raw_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [
        {
            "text": "Cancelling less than 24 hours in advance, or no-show: 50 USD.",
            "source_document": "appointment-policy",
            "section": "Cancellation policy",
        }
    ]
    monkeypatch.setattr(rag_pipeline, "retrieve", lambda *_args, **_kwargs: chunks)
    monkeypatch.setattr(
        rag_pipeline,
        "generate_answer",
        lambda question, context: "For private-pay patients, a cancellation under 24 hours is $50.",
    )
    answer = rag_pipeline.query("Is there a charge for cancelling 12 hours in advance?")
    assert answer == "For private-pay patients, a cancellation under 24 hours is $50."
    assert chunks[0]["text"] not in answer
    assert answer != chunks[0]["text"]
