"""Retrieve HealthCore policy chunks and generate a coordinator-facing answer."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from data.process.rag import (
    COLLECTION,
    DEFAULT_MIN_SCORE,
    embed,
    chat_model_candidates,
    get_qdrant_client,
    provider_http_error,
    rag_api_key,
    rag_base_url,
)


def _points_from_client(qdrant: Any, vector: list[float], k: int) -> list[Any]:
    try:
        if hasattr(qdrant, "query_points"):
            return qdrant.query_points(
                collection_name=COLLECTION,
                query=vector,
                limit=k,
                with_payload=True,
            ).points
        return qdrant.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=k,
            with_payload=True,
        )
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise RuntimeError(
                f"Qdrant collection {COLLECTION} is not indexed. "
                "Start Qdrant and run: uv run python scripts/index_knowledge.py"
            ) from exc
        raise
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        text = str(exc).lower()
        if status == 404 or "not found" in text or "doesn't exist" in text:
            raise RuntimeError(
                f"Qdrant collection {COLLECTION} is not indexed. "
                "Start Qdrant and run: uv run python scripts/index_knowledge.py"
            ) from exc
        if any(
            token in text
            for token in ("connect", "connection refused", "timed out", "name or service")
        ):
            raise RuntimeError(
                "Cannot reach Qdrant. Start it with `docker compose up -d qdrant` "
                "and set QDRANT_URL (default http://127.0.0.1:6333)."
            ) from exc
        raise

logger = logging.getLogger(__name__)

NO_INFORMATION = (
    "I don't have enough information in the HealthCore knowledge base to answer "
    "that reliably. Please check with billing (Tom Callahan) or clinical operations "
    "rather than guessing coverage, fees, or timeframes."
)

SYSTEM_PROMPT = """You are the clinic's best service salesperson, speaking to a HealthCore patient coordinator on Priya Nair's desk team.

Rules:
- Be clear and empathetic. Never invent insurance coverage, fees, or timeframes.
- Use ONLY the retrieved policy context. If a fact is not in the context, do not add it.
- When the question does not specify country, distinguish United States vs United Kingdom coverage.
- For an insurer not listed in the context, say coverage must be verified with billing (Tom Callahan). Never confirm undocumented coverage.
- Never apply a no-show or late-cancellation fee to Medicare or Medicaid patients.
- Never include real or simulated patient names, MRNs, diagnoses, or other PHI.
- If the context is empty, say there is not enough information in the knowledge base.
"""


def retrieve(
    query: str,
    *,
    k: int = 5,
    min_score: float | None = None,
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """Embed the question, search Qdrant, drop hits below ``min_score``. Returns payloads."""
    floor = DEFAULT_MIN_SCORE if min_score is None else min_score
    vector = embed(query)
    qdrant = client if client is not None else get_qdrant_client()
    hits = _points_from_client(qdrant, vector, k)
    results: list[dict[str, Any]] = []
    for hit in hits:
        score = float(hit.score) if hit.score is not None else 0.0
        if score < floor:
            continue
        payload = dict(hit.payload or {})
        payload["score"] = score
        results.append(payload)
    logger.debug(
        "retrieve query=%r k=%s min_score=%s kept=%s sources=%s",
        query[:80],
        k,
        floor,
        len(results),
        [row.get("source_document") for row in results],
    )
    return results


def _format_context(context: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, row in enumerate(context, start=1):
        source = row.get("source_document", "unknown")
        section = row.get("section", "")
        text = row.get("text", "")
        blocks.append(f"[{index}] source={source} section={section}\n{text}")
    return "\n\n".join(blocks)


def generate_answer(question: str, context: list[dict[str, Any]]) -> str:
    """Generation LLM only. Empty context → honest refusal, no invented facts."""
    if not context:
        return NO_INFORMATION
    key = rag_api_key()
    if not key:
        raise RuntimeError(
            "LLM_API_KEY / RAG_API_KEY / FOURGEEKS_API_KEY / OPENAI_API_KEY is required to generate answers"
        )
    user = (
        f"Coordinator question:\n{question.strip()}\n\n"
        f"Retrieved HealthCore policy context:\n{_format_context(context)}"
    )
    response: httpx.Response | None = None
    last_error: httpx.Response | None = None
    for model in chat_model_candidates():
        for attempt in range(4):
            response = httpx.post(
                f"{rag_base_url()}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=45.0,
            )
            if response.status_code == 429 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            break
        assert response is not None
        if response.status_code in {400, 404} and "model" in (response.text or "").lower():
            last_error = response
            logger.warning("chat model %s unavailable (%s); trying next catalog id", model, response.status_code)
            continue
        last_error = response
        break
    assert response is not None
    if response.is_error:
        raise provider_http_error("Chat completions", last_error or response)
    content = response.json()["choices"][0]["message"]["content"]
    return str(content).strip()


def query(question: str) -> str:
    """Only entry point for HTTP/UI: retrieve then generate."""
    context = retrieve(question, k=5, min_score=DEFAULT_MIN_SCORE)
    return generate_answer(question, context)
