# HealthCore desk knowledge — RAG design

Priya Nair’s patient coordinators ask policy questions at the desk. This stack answers from four official HealthCore documents. The client only ever sees a **generated** string — never Qdrant hits.

## Process

```text
docs/company-knowledge-base/*.md
        │
        ▼
setup()  — parse + semantic chunks + embed(chunk)
        │
        ▼
Qdrant collection healthcore_knowledge  (Cosine)
        │
coordinator question
        │
        ▼
retrieve()  — embed(question) → top-k → drop score < min_score
        │
        ▼
generate_answer()  — system prompt + chunk text → generation LLM
        │
        ▼
query()  — retrieve + generate_answer  (only function HTTP/UI call)
        │
        ▼
POST /knowledge/query  →  { "answer": "…" }
        │
        ▼
Backoffice /knowledge  (Desk knowledge)
```

Index: `uv run python scripts/index_knowledge.py`  
Recall: `uv run python scripts/eval_rag_recall.py`

## Chunking

Sources are copied from `00-general-contexts/healthcore/` (4Geeks syllabus) into `docs/company-knowledge-base/` **without rewriting policy text**.

`setup()` splits each file on **section start markers** that already exist in the official Markdown (e.g. `United States (Texas, Florida, Georgia):`, `Cancellation policy:`, numbered referral steps). A chunk is one heading/rule block. We do **not** split mid-sentence, and Medicare/Medicaid no-show language stays in the same cancellation chunk as the 50 USD / 40 GBP private-pay fee.

Approximate counts (must be ≥ 3 per file):

| `source_document` | Typical chunks |
| --- | --- |
| `insurance-coverage` | US, UK, unlisted-insurer / billing |
| `appointment-policy` | Booking, cancellation (incl. Medicare/Medicaid), reminders, 3 no-shows |
| `referral-process` | Intro, numbered steps, 11-day average, 5-day escalate, outside network |
| `new-patient-checklist` | Required items, documents to bring, incomplete history |

Payload fields match CONTEXT §3: `company=healthcore`, `language=en`, `source_document` slugs above, `section`, `chunk_index`, `text`.

**Idempotency:** point IDs are `uuid5(NAMESPACE_URL, "healthcore:{source_document}:{chunk_index}")`. Re-running `setup()` upserts the same IDs.

## Embedding practices

| Role | Model ID | Notes |
| --- | --- | --- |
| Embeddings | `text-embedding-3-small` (`RAG_EMBEDDING_MODEL`) | 4Geeks student OpenAI-compatible embeddings. Used by **`embed()`** for chunks **and** questions. |
| Generation | `gpt-4o-mini` (`RAG_GENERATION_MODEL`) | Different ID. Chat completions only, in `generate_answer()`. |

Set `RAG_API_KEY` or `FOURGEEKS_API_KEY` and optional `RAG_BASE_URL` / `FOURGEEKS_BASE_URL`. If no key is set, `embed()` falls back to a **384-d hashed character 3-gram** (L2-normalized) so local index/Recall@3 still run; `generate_answer()` still requires a key (empty retrieve returns the honest “not enough information” string without an LLM).

| Qdrant | Value |
| --- | --- |
| Collection | `healthcore_knowledge` |
| Distance | Cosine |
| Dimension | `len(embed(sample))` — 1536 with `text-embedding-3-small`, 384 with the offline fallback |
| `min_score` | **0.35** (`RAG_MIN_SCORE`) — below this, junk neighbours are dropped. Recall@3 is measured at `min_score=0` so the 80% bar is about ranking, not the floor. Tune the floor up if coordinators see off-topic answers; keep Recall@3 ≥ 80% on `data/eval/test-queries.json`. |

Text is whitespace-normalized before embed. No PHI is stored: policy text only.

## Voice and constraints

Generation prompt: best service salesperson → coordinator. US vs UK when country is omitted. Unlisted insurer → verify with Tom Callahan / billing. No Medicare/Medicaid no-show fee. No invented fees or coverage. No PHI.
