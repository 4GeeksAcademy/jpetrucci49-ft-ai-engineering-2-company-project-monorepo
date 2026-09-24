"""Chunk and index HealthCore desk-policy documents into Qdrant.

Corpus: ``docs/company-knowledge-base/``. Collection: ``healthcore_knowledge``.
``embed()`` is used at index time and again for the coordinator's question.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
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
DEFAULT_QDRANT_URL = "http://127.0.0.1:6333"
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
_listed_model_ids: list[str] | None = None


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _env_value(*names: str, default: str = "") -> str:
    """Read the first non-empty env var, stripping quotes and inline comments."""
    for name in names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        value = raw.strip()
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        value = value.strip('"').strip("'")
        if value:
            return value
    return default


def embedding_model_id() -> str:
    return _env_value(
        "LLM_EMBEDDING_MODEL", "RAG_EMBEDDING_MODEL", default="text-embedding-3-small"
    )


def generation_model_id() -> str:
    return _env_value("LLM_MODEL", "RAG_GENERATION_MODEL", default="gpt-4o-mini")


def listed_model_ids() -> list[str]:
    """Provider ``/models`` ids. Cached. Empty when offline or the call fails."""
    global _listed_model_ids
    if _listed_model_ids is not None:
        return _listed_model_ids
    key = rag_api_key()
    if not key:
        _listed_model_ids = []
        return _listed_model_ids
    try:
        response = httpx.get(
            f"{rag_base_url()}/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=20.0,
        )
        if response.is_error:
            _listed_model_ids = []
            return _listed_model_ids
        payload = response.json()
        items = payload.get("data", payload if isinstance(payload, list) else [])
        _listed_model_ids = [str(item.get("id", "")) for item in items if item.get("id")]
    except Exception:
        _listed_model_ids = []
    return _listed_model_ids


def resolve_model_id(configured: str, *, embedding: bool = False) -> str:
    """Map lesson/OpenAI ids onto the gateway catalog (drop a ``litellm/`` prefix)."""
    ids = listed_model_ids()
    if not ids:
        return configured
    for candidate in (configured, configured.removeprefix("litellm/")):
        if candidate in ids:
            return candidate
    if embedding:
        for item in ids:
            if "embed" in item.lower():
                return item
        return configured
    for item in ids:
        if "embed" not in item.lower() and ("gpt" in item.lower() or "openai" in item.lower()):
            return item
    for item in ids:
        if "embed" not in item.lower():
            return item
    return configured


def chat_model_candidates() -> list[str]:
    """Configured chat model first, then other non-embedding catalog ids (OpenAI/GPT preferred)."""
    primary = resolve_model_id(generation_model_id())
    chat = [item for item in listed_model_ids() if "embed" not in item.lower()]
    preferred = [item for item in chat if "openai" in item.lower() or "gpt" in item.lower()]
    rest = [item for item in chat if item not in preferred]
    ordered: list[str] = []
    for item in (primary, *preferred, *rest):
        if item and item not in ordered:
            ordered.append(item)
    return ordered or [primary]


def rag_api_key() -> str:
    return _env_value("LLM_API_KEY", "RAG_API_KEY", "FOURGEEKS_API_KEY", "OPENAI_API_KEY")


def rag_base_url() -> str:
    explicit = _env_value(
        "LLM_API_URL", "RAG_BASE_URL", "FOURGEEKS_BASE_URL", "OPENAI_BASE_URL"
    ).rstrip("/")
    if explicit:
        return explicit
    fourgeeks_only = bool(os.environ.get("FOURGEEKS_API_KEY", "").strip()) and not (
        os.environ.get("LLM_API_KEY", "").strip()
        or os.environ.get("RAG_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )
    if fourgeeks_only:
        raise RuntimeError(
            "FOURGEEKS_API_KEY is set but FOURGEEKS_BASE_URL / RAG_BASE_URL / LLM_API_URL is missing. "
            "Use the OpenAI-compatible base URL from the 4Geeks course card (ends with /v1). "
            "A 4Geeks student key is rejected by https://api.openai.com/v1 (HTTP 401)."
        )
    return "https://api.openai.com/v1"


def provider_http_error(action: str, response: httpx.Response) -> RuntimeError:
    """Map provider HTTP failures to a 503-friendly message. Never include the key."""
    endpoint = str(response.request.url).split("?", 1)[0]
    hint = {
        401: "The key was rejected. Check LLM_API_KEY and LLM_API_URL.",
        403: "The gateway refused this model or key (wrong id, or budget exhausted).",
        429: "The provider rate-limited the request. Wait a minute and retry.",
    }.get(
        response.status_code,
        "Check LLM_API_KEY / LLM_API_URL and that the key matches that host.",
    )
    detail = ""
    try:
        payload = response.json()
        err = payload.get("error", payload)
        if isinstance(err, dict):
            detail = str(err.get("message") or err.get("detail") or "")
        elif isinstance(err, str):
            detail = err
    except Exception:
        detail = (response.text or "")[:180]
    extra = f" Provider: {detail.strip()}" if detail.strip() else ""
    return RuntimeError(
        f"{action} failed with HTTP {response.status_code} at {endpoint}. {hint}{extra}"
    )


def _retry_wait_seconds(response: httpx.Response, attempt: int) -> float:
    raw = response.headers.get("retry-after")
    if raw:
        try:
            return min(float(raw), 60.0)
        except ValueError:
            pass
    return min(2 ** (attempt + 1), 30.0)


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


def embed_many(texts: list[str]) -> list[list[float]]:
    """Embed many strings in one provider request. Same model as ``embed()``."""
    cleaned = [_normalize_text(text) for text in texts]
    if not cleaned or any(not item for item in cleaned):
        raise ValueError("cannot embed empty text")
    key = rag_api_key()
    if not key:
        return [_local_embed(item) for item in cleaned]
    url = f"{rag_base_url()}/embeddings"
    response: httpx.Response | None = None
    model = resolve_model_id(embedding_model_id(), embedding=True)
    for attempt in range(6):
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "input": cleaned},
            timeout=60.0,
        )
        if response.status_code == 429 and attempt < 5:
            time.sleep(_retry_wait_seconds(response, attempt))
            continue
        if response.status_code in {400, 401, 403, 404} and attempt == 0:
            global _listed_model_ids
            _listed_model_ids = None
            retry_model = resolve_model_id(embedding_model_id(), embedding=True)
            if retry_model != model:
                model = retry_model
                continue
        break
    assert response is not None
    if response.is_error:
        raise provider_http_error("Embeddings", response)
    rows = sorted(response.json()["data"], key=lambda row: int(row.get("index", 0)))
    return [[float(value) for value in row["embedding"]] for row in rows]


def embed(text: str) -> list[float]:
    """Vector for one string. Same function for chunks and the user question."""
    return embed_many([text])[0]


def qdrant_url() -> str:
    raw = os.environ.get("QDRANT_URL", DEFAULT_QDRANT_URL).strip()
    return raw or DEFAULT_QDRANT_URL


def get_qdrant_client() -> QdrantClient:
    """HTTP Qdrant at ``QDRANT_URL`` (default localhost:6333). ``:memory:`` is test/offline only."""
    global _memory_client
    url = qdrant_url()
    if url in {":memory:", "memory"}:
        if _memory_client is None:
            _memory_client = QdrantClient(":memory:")
        return _memory_client
    return QdrantClient(url=url, check_compatibility=False)


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


def _collection_vector_size(client: QdrantClient) -> int | None:
    try:
        info = client.get_collection(COLLECTION)
    except Exception:
        return None
    vectors = getattr(getattr(info.config, "params", None), "vectors", None)
    size = getattr(vectors, "size", None)
    return int(size) if size is not None else None


def setup() -> int:
    """Parse the four CONTEXT files, embed, upsert. Re-run updates the same UUID5 IDs."""
    chunks = load_knowledge_chunks()
    vectors = embed_many([chunk["text"] for chunk in chunks])
    dim = len(vectors[0])
    client = get_qdrant_client()
    existing = {collection.name for collection in client.get_collections().collections}
    if COLLECTION in existing and _collection_vector_size(client) != dim:
        client.delete_collection(COLLECTION)
        existing.discard(COLLECTION)
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    points = [
        PointStruct(
            id=point_id(chunk["source_document"], int(chunk["chunk_index"])),
            vector=vectors[index],
            payload=chunk,
        )
        for index, chunk in enumerate(chunks)
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    return len(points)
