"""Retrieve HealthCore policy chunks and generate a coordinator-facing answer."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from data.process.rag import (
    COLLECTION,
    DEFAULT_MIN_SCORE,
    embed,
    generation_model_id,
    get_qdrant_client,
    rag_api_key,
    rag_base_url,
)

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
    if hasattr(qdrant, "query_points"):
        hits = qdrant.query_points(
            collection_name=COLLECTION,
            query=vector,
            limit=k,
            with_payload=True,
        ).points
    else:
        hits = qdrant.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=k,
            with_payload=True,
        )
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
            "RAG_API_KEY / FOURGEEKS_API_KEY / OPENAI_API_KEY is required to generate answers"
        )
    user = (
        f"Coordinator question:\n{question.strip()}\n\n"
        f"Retrieved HealthCore policy context:\n{_format_context(context)}"
    )
    response = httpx.post(
        f"{rag_base_url()}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": generation_model_id(),
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
        },
        timeout=45.0,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return str(content).strip()


def query(question: str) -> str:
    """Only entry point for HTTP/UI: retrieve then generate."""
    context = retrieve(question, k=5, min_score=DEFAULT_MIN_SCORE)
    return generate_answer(question, context)
