"""Unit tests for HealthCore RAG retrieve/query. No live Qdrant or LLM."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from data.pipelines import rag as rag_pipeline
from data.process import rag as rag_process


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


def test_fourgeeks_key_requires_course_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_URL", raising=False)
    monkeypatch.delenv("RAG_BASE_URL", raising=False)
    monkeypatch.delenv("FOURGEEKS_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("RAG_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("FOURGEEKS_API_KEY", "student-token")
    with pytest.raises(RuntimeError, match="FOURGEEKS_BASE_URL"):
        rag_process.rag_base_url()


def test_embed_many_offline_matches_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("RAG_API_KEY", raising=False)
    monkeypatch.delenv("FOURGEEKS_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    texts = ["Cancellation policy: 24 hours.", "Bring insurance card and ID."]
    batch = rag_process.embed_many(texts)
    assert len(batch) == 2
    assert batch[0] == rag_process.embed(texts[0])
    assert len(batch[0]) == rag_process.LOCAL_EMBED_DIM


def test_resolve_model_id_picks_gateway_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rag_process,
        "listed_model_ids",
        lambda: [
            "downtown-miami/openai/gpt-5.6-luna",
            "downtown-miami/openrouter/perplexity/pplx-embed-v1-0.6b",
        ],
    )
    assert (
        rag_process.resolve_model_id("text-embedding-3-small", embedding=True)
        == "downtown-miami/openrouter/perplexity/pplx-embed-v1-0.6b"
    )
    assert (
        rag_process.resolve_model_id("litellm/downtown-miami/openai/gpt-5.6-luna")
        == "downtown-miami/openai/gpt-5.6-luna"
    )
    monkeypatch.setattr(rag_process, "generation_model_id", lambda: "litellm/downtown-miami/groq/llama-3.1-8b-instant")
    monkeypatch.setattr(
        rag_process,
        "listed_model_ids",
        lambda: [
            "downtown-miami/groq/llama-3.1-8b-instant",
            "downtown-miami/openai/gpt-5.6-luna",
            "downtown-miami/openrouter/perplexity/pplx-embed-v1-0.6b",
        ],
    )
    assert rag_process.chat_model_candidates()[0] == "downtown-miami/groq/llama-3.1-8b-instant"
    assert "downtown-miami/openai/gpt-5.6-luna" in rag_process.chat_model_candidates()
    assert all("embed" not in item for item in rag_process.chat_model_candidates())


def test_env_value_strips_lesson_comment_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_URL", 'https://api.openai.com/v1" # or any compatible gateway')
    monkeypatch.setenv("LLM_MODEL", 'gpt-4o-mini" # or your preferred chat model')
    monkeypatch.delenv("RAG_BASE_URL", raising=False)
    monkeypatch.delenv("FOURGEEKS_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("RAG_GENERATION_MODEL", raising=False)
    assert rag_process.rag_base_url() == "https://api.openai.com/v1"
    assert rag_process.generation_model_id() == "gpt-4o-mini"


def test_course_llm_env_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_API_URL", "https://gateway.example/v1")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.delenv("RAG_API_KEY", raising=False)
    monkeypatch.delenv("FOURGEEKS_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("RAG_BASE_URL", raising=False)
    monkeypatch.delenv("FOURGEEKS_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("RAG_GENERATION_MODEL", raising=False)
    assert rag_process.rag_api_key() == "sk-test"
    assert rag_process.rag_base_url() == "https://gateway.example/v1"
    assert rag_process.generation_model_id() == "gpt-4o-mini"


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


def test_retrieve_missing_collection_is_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Missing:
        def query_points(self, **_: object) -> None:
            raise ValueError("Collection healthcore_knowledge not found")

    monkeypatch.setattr(rag_pipeline, "embed", lambda _: [0.1, 0.2])
    with pytest.raises(RuntimeError, match="not indexed"):
        rag_pipeline.retrieve("first appointment", client=_Missing())


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
