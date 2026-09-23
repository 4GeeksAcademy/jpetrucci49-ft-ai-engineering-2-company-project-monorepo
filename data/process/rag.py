"""Chunk and index HealthCore desk-policy documents into Qdrant.

Corpus: ``docs/company-knowledge-base/``. Collection: ``healthcore_knowledge``.
``embed()`` is used at index time and again for the coordinator's question.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

REPO_ROOT = Path(os.environ.get("HEALTHCORE_REPO_ROOT", "")).resolve() if os.environ.get(
    "HEALTHCORE_REPO_ROOT"
) else Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = REPO_ROOT / "docs" / "company-knowledge-base"
COLLECTION = os.environ.get("QDRANT_COLLECTION", "healthcore_knowledge")
COMPANY = "healthcore"
LANGUAGE = "en"
DEFAULT_MIN_SCORE = float(os.environ.get("RAG_MIN_SCORE", "0.35"))
LOCAL_EMBED_DIM = 384
POINT_NAMESPACE = uuid.NAMESPACE_URL

SOURCE_FILES: dict[str, str] = {
    "healthcore-insurance-coverage.en.md": "insurance-coverage",
    "healthcore-appointment-policy.en.md": "appointment-policy",
    "healthcore-referral-process.en.md": "referral-process",
    "healthcore-new-patient-checklist.en.md": "new-patient-checklist",
}

# Split on these line-start markers so US/UK, Medicare/Medicaid, and numbered
# rules stay whole. Markers are unique prefixes of the official files.
_SECTION_STARTS: dict[str, tuple[str, ...]] = {
    "insurance-coverage": (
        "United States (Texas, Florida, Georgia):",
        "United Kingdom (London and Manchester):",
        "No coordinator should confirm coverage",
    ),
    "appointment-policy": (
        "Booking appointments:",
        "Cancellation policy:",
        "Automated reminders:",
        "A patient with 3 no-shows",
    ),
    "referral-process": (
        "When a primary care physician refers",
        "1. The physician creates the referral",
        "Target completed-referral time:",
        "If a patient hasn't received appointment options",
        "Referrals to specialists outside",
    ),
    "new-patient-checklist": (
        "Every new patient must complete",
        "1. Medical history form",
        "Documents the patient should bring",
        "A new patient who hasn't completed the medical history",
    ),
}

_memory_client: QdrantClient | None = None


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def embedding_model_id() -> str:
    return os.environ.get("RAG_EMBEDDING_MODEL", "text-embedding-3-small")


def generation_model_id() -> str:
    return os.environ.get("RAG_GENERATION_MODEL", "gpt-4o-mini")


def rag_api_key() -> str:
    return (
        os.environ.get("RAG_API_KEY")
        or os.environ.get("FOURGEEKS_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )


def rag_base_url() -> str:
    return (
        os.environ.get("RAG_BASE_URL")
        or os.environ.get("FOURGEEKS_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).rstrip("/")


def _local_embed(text: str) -> list[float]:
    """Unit-length hashed 3-grams. Offline fallback when no 4Geeks/OpenAI key."""
    vector = np.zeros(LOCAL_EMBED_DIM, dtype=np.float64)
    cleaned = _normalize_text(text).lower()
    if len(cleaned) < 3:
        cleaned = (cleaned + "   ")[:3]
    for index in range(len(cleaned) - 2):
        gram = cleaned[index : index + 3]
        digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
        slot = int.from_bytes(digest, "little") % LOCAL_EMBED_DIM
        sign = 1.0 if digest[0] % 2 == 0 else -1.0
        vector[slot] += sign
    norm = np.linalg.norm(vector)
    if norm == 0:
        vector[0] = 1.0
        norm = 1.0
    return (vector / norm).astype(np.float32).tolist()


def embed(text: str) -> list[float]:
    """Vector for one string. Same function for chunks and the user question."""
    cleaned = _normalize_text(text)
    if not cleaned:
        raise ValueError("cannot embed empty text")
    key = rag_api_key()
    if not key:
        return _local_embed(cleaned)
    url = f"{rag_base_url()}/embeddings"
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": embedding_model_id(), "input": cleaned},
        timeout=30.0,
    )
    response.raise_for_status()
    payload = response.json()
    vector = payload["data"][0]["embedding"]
    return [float(value) for value in vector]


def get_qdrant_client() -> QdrantClient:
    """HTTP Qdrant when ``QDRANT_URL`` is set; otherwise a process-wide in-memory client."""
    global _memory_client
    url = os.environ.get("QDRANT_URL", "").strip()
    if url:
        return QdrantClient(url=url)
    if _memory_client is None:
        _memory_client = QdrantClient(":memory:")
    return _memory_client


def _split_on_markers(body: str, markers: tuple[str, ...]) -> list[tuple[str, str]]:
    """Return (section_label, text) pairs without cutting inside a marker block."""
    positions: list[tuple[int, str]] = []
    for marker in markers:
        found = body.find(marker)
        if found >= 0:
            positions.append((found, marker))
    positions.sort(key=lambda item: item[0])
    if not positions:
        return [("Overview", body.strip())]

    chunks: list[tuple[str, str]] = []
    preamble = body[: positions[0][0]].strip()
    if preamble and preamble not in {"# Accepted Insurance Coverage"}:
        title = preamble.splitlines()[0].lstrip("# ").strip() or "Overview"
        if len(_normalize_text(preamble)) > 40:
            chunks.append((title, preamble))

    for index, (start, marker) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(body)
        block = body[start:end].strip()
        if block:
            chunks.append((marker.rstrip(":"), block))
    return chunks


def chunk_source_document(source_document: str, markdown: str) -> list[dict[str, Any]]:
    markers = _SECTION_STARTS[source_document]
    sections = _split_on_markers(markdown, markers)
    chunks: list[dict[str, Any]] = []
    for index, (section, text) in enumerate(sections):
        body = text.strip()
        if not body:
            continue
        chunks.append(
            {
                "company": COMPANY,
                "source_document": source_document,
                "section": section[:200],
                "language": LANGUAGE,
                "chunk_index": index,
                "text": body,
            }
        )
    if len(chunks) < 3:
        raise ValueError(f"{source_document} produced {len(chunks)} chunks; need at least 3")
    return chunks


def load_knowledge_chunks() -> list[dict[str, Any]]:
    if not KNOWLEDGE_DIR.is_dir():
        raise FileNotFoundError(f"knowledge base missing: {KNOWLEDGE_DIR}")
    chunks: list[dict[str, Any]] = []
    for filename, source_document in SOURCE_FILES.items():
        path = KNOWLEDGE_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(f"CONTEXT source missing: {path}")
        chunks.extend(chunk_source_document(source_document, path.read_text(encoding="utf-8")))
    return chunks


def point_id(source_document: str, chunk_index: int) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, f"healthcore:{source_document}:{chunk_index}"))


def setup() -> int:
    """Parse the four CONTEXT files, embed, upsert. Re-run updates the same UUID5 IDs."""
    chunks = load_knowledge_chunks()
    sample = embed(chunks[0]["text"])
    dim = len(sample)
    client = get_qdrant_client()
    existing = {collection.name for collection in client.get_collections().collections}
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    points = [
        PointStruct(
            id=point_id(chunk["source_document"], int(chunk["chunk_index"])),
            vector=embed(chunk["text"]),
            payload=chunk,
        )
        for chunk in chunks
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    return len(points)
