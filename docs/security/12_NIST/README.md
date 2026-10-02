# NIST report — model input map

Written before any 12.x code change. This file is the inventory and the list of every place a model receives outside text. The six-function report is not this file.

No patient identifier, diagnosis, or clinical content belongs in this folder, in tests, or in logs. HIPAA (US, 60-day notice, BAA, notify the individual and HHS) and UK GDPR (UK, 72-hour notice to the ICO, DPA) are separate regimes.

## Inventory

An owner is the person accountable for the control. When a vendor hosts the model, Claire Whitfield owns the BAA (US) or DPA (UK). James Osei owns the key in the gitignored env file. This repo does not store that key.

| Component | In this fork | Owner | Third-party control |
| --- | --- | --- | --- |
| Clinical documentation assistant | Not built. No SOAP route. | Dr. Marcus Reid would own it. | None here. |
| Patient referral and lab notification | Not built. No patient-notify route. | Dr. Marcus Reid would own it. | None here. |
| RAG over clinic policy | `data/pipelines/rag.py`, `data/process/rag.py`, Qdrant `healthcore_knowledge`, `POST /knowledge/query` | Claire Whitfield (what the policy says). James Osei (index, bind, model key). | Chat and embedding calls use `LLM_API_KEY` / `LLM_API_URL` / `LLM_MODEL`. |
| Compliance agent | `services/api/agent/` (`desk_graph`, `POST /agent/query`, `WS /agent/chat`) | Claire Whitfield | Same model vendor as RAG. The graph does not call a second model. |
| Desk memory | `services/api/agent/memory/` | Claire Whitfield (what may be stored). The signed-in staff member confirms each note before it is kept. | Local TinyDB. Not a model vendor. |
| MCP tools | `mcps/healthcore/` incidents and read-only inventory | James Osei (server). Tom Callahan (inventory facts). | First-party. Tool JSON is not sent to the model. |
| RFP intake classifier | `data/pipelines/rfp_intake/classify.py` | Claire Whitfield (accept or discard). | Optional chat call on the same vendor key. Deterministic fallback runs when the call is absent. |
| RFP draft and approval | `data/pipelines/rfp_draft/`, `data/pipelines/rfp_approval/` | Tom Callahan (revenue), Dr. Marcus Reid (clinical), Claire Whitfield (compliance). A human decision changes status. | No model call. |
| Access record | Guardrail counts and `data/eval/agent_traces/`. Not a clinical chart. | James Osei | None. |
| Operations dashboard and SSE | Backoffice `/` and `/reporting`. Event `rfp_ticket_created` only. | Tom Callahan and Dr. Marcus Reid for the figures. James Osei for the stream. | No model call. |
| Sales forecast | `scripts/forecast_sales.py` (XGBoost) | Tom Callahan | No language model. |

## Where a model receives outside text

Only two chat-completion call sites and one embeddings call site exist. System prompt text in `data/pipelines/rag.py` is not outside input.

### 1. Compliance and policy answer

`generate_answer` in `data/pipelines/rag.py` posts `chat/completions`. Callers:

- `POST /knowledge/query` via `query()`
- `generate_policy` in `services/api/agent/nodes.py` for `POST /agent/query` and `WS /agent/chat`

The user message is built by `_user_prompt`. Three outside strings can sit in it:

| Source | How it arrives | How it is marked today |
| --- | --- | --- |
| Staff question | JSON body, or a `user_message` frame | Labeled “Staff question (user input, not system instructions)” |
| Approved memory notes | `wrap_question` in `services/api/agent/memory/store.py` prefixes the question | Labeled “Operator-approved notes”. Not wrapped as an untrusted source. |
| Retrieved policy chunks | `retrieve()` payloads, then `wrap_context` | `BEGIN_UNTRUSTED_SOURCE` … `END_UNTRUSTED_SOURCE` |

Empty retrieval never calls the model. It returns the fixed “not enough information” line.

The embedding model also receives the staff question: `retrieve()` calls `embed(query)` before the search.

### 2. Knowledge-base documents at index time

`embed_many` in `data/process/rag.py` posts `/embeddings`. Input is chunk text from `docs/company-knowledge-base/` (`scripts/index_knowledge.py`). That text is later returned by search and enters path 1 inside the untrusted markers. A poisoned policy file is an indirect injection at generation time, not at embed time.

### 3. Uploaded RFP markdown

`_llm_classify` in `data/pipelines/rfp_intake/classify.py` posts `chat/completions` when a model key is set. The user message is the first 6000 characters of the converted upload, with no untrusted markers. The system message is a short classify instruction. If the call fails or no key is set, `classify_rfp_fallback` decides.

Draft generation, department workers, and approval do not call a model. They copy fields from the intake handoff.

### 4. MCP tool results do not reach a model

`lookup_incident` and `lookup_inventory` return structured rows. `ticket_sentence` and `stock_sentence` are appended in `_attach_tool_sentences` after `generate_answer` returns. The model does not see tool JSON, ticket text, or stock text.

## What this map does not include

Forecasting, telemetry, reporting, and SSE do not send text to a language model. There is no SOAP generator and no patient-notification sender in this repo.
