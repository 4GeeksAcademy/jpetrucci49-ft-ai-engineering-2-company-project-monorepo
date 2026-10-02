# HealthCore Monorepo — Progress

_Last updated: NIST CSF 2.0 report and urgent AI protections (12)_

## Completed

### Milestone 1 — Public website

- [x] Migrated to `uis/website/` (Next.js App Router)
- [x] Routes: `/` landing, `/application` patient enquiry form
- [x] Bilingual EN/ES, Schema.org, responsive mobile navigation
- [x] Legacy root HTML removed

### Milestone 2 — TypeScript utilities

- [x] `src/utils/` — collections, search, transformations, validations
- [x] `src/utility-registry.ts` — shared function catalog for testers
- [x] Vitest coverage in `tests/utils/`

### Milestone 3 — Talent Pipeline Tracker

- [x] `uis/talent-pipeline-tracker/` on port 3002

### Milestone 4 — Agent infrastructure & Next.js apps

- [x] `memory-bank/`, root `AGENTS.md`, `.agents/`, `skills/monday-operations-brief/`
- [x] `uis/backoffice/` — operations dashboard + `/utilities` tester
- [x] Root `npm run dev` serves all apps concurrently
- [x] Dev hub at `public/index.html` (port 4173)

### Milestone 5 — Incident report analysis

**Phase 1**

- [x] Python environment via uv (`pyproject.toml`, `uv.lock`)
- [x] `scripts/analyze.py` — CSV validation, console report, optional CSV export

**Phase 2**

- [x] Shared analysis module at `services/api/app/incidents/analysis.py`
- [x] FastAPI service — `POST /api/incidents/analyze`, `GET /api/incidents/results/export`
- [x] Backoffice `/incidents` page — upload, summary, CSV download
- [x] Root `npm run dev:api`; CLI refactored to import shared module

### Milestone 6 — Supplier directory (Lightweight Storage API)

**Step 1 — Data model**

- [x] Spec: `specs/06_SPECS_DATA.md`
- [x] `services/api/models.py` — Pydantic enums, `SupplierCreate` / `SupplierUpdate` / `SupplierRateUpdate` / `SupplierStatusUpdate` / `Supplier`
- [x] Validation: status enum, positive `monthly_rate`, category whitelist, country–currency pairing

**Step 2 — Seeder**

- [x] Spec: `specs/06_SPECS_SEEDER.md`
- [x] `services/api/database.py` — TinyDB init (`suppliers.json`, `get_suppliers_table()`)
- [x] `services/api/seed.py` — 15 context suppliers, idempotent by `name` + `country`
- [x] `uv run seed` from `services/api/`

**Step 3 — API endpoints**

- [x] Spec: `specs/06_SPECS_ENDPOINTS.md`
- [x] `services/api/routes/suppliers.py` — CRUD + rate/status PATCH
- [x] Mounted in `app/main.py` at `/suppliers`

**Step 4 — Frontend**

- [x] Spec: `specs/06_SPECS_FRONTEND.md`
- [x] `uis/backoffice/app/suppliers` — directory page with filters, collapsible registration form, rate/status controls (suspend only — no delete in UI)
- [x] BFF routes at `app/api/suppliers/*`; nav link in `BackofficeShell`

### Milestone 7 — Authentication (AUTH-01)

- [x] Spec: `specs/07_SPECS.md`
- [x] `services/api/auth/` — models, TinyDB (`auth.json`), libpass bcrypt, PyJWT HS256
- [x] Routes: `POST /auth/login`, `GET /auth/me`, `/users` CRUD, `/profiles/me`
- [x] `get_current_user`, `require_admin`, `require_self_or_admin` dependencies
- [x] Protected all supplier and incident handlers; public only login + registration + docs
- [x] `JWT_SECRET` required at startup; documented in `.env.example`

### Milestone 8 — Frontend authentication (AUTH-02)

- [x] Spec: `specs/08_SPECS.md`
- [x] `packages/shared/auth/` — token storage, `authFetch`, shared login/register/profile forms
- [x] Backoffice + talent tracker: `/login`, `/register`, `/account/profile`, `AuthGuard`, logout
- [x] BFF auth routes; incident/supplier proxies forward `Authorization`
- [x] `uis/website/` unchanged (fully public)

### Milestone 9 — Password recovery and change (AUTH-03)

**Phase 1 — Backend**

- [x] Spec: `specs/09_SPECS_BACK.md`
- [x] `POST /auth/forgot-password`, `/auth/reset-password`, `/auth/change-password`
- [x] TinyDB `password_reset_tokens` table; opaque single-use tokens (SHA-256 hash stored)
- [x] Resend email integration for password reset links
- [x] Env vars documented in `services/api/.env.example` and README

**Phase 2 — Frontend**

- [x] Spec: `specs/09_SPECS_FRONT.md`
- [x] `/forgot-password`, `/reset-password`, `/account/change-password` in internal apps
- [x] BFF proxies; login forgot link; profile change-password link

### Milestone 10 — Authentication API unit tests (AUTH-088)

- [x] Spec: `specs/10_SPECS.md`; test plan: `TESTING.md`
- [x] `services/api/tests/` — pytest suite (**89** tests) with isolated TinyDB fixtures
- [x] Coverage **91%** on `auth/` (`uv run pytest --cov=auth`)
- [x] Jest config (`jest.config.mjs`) + tests in `packages/shared/auth/__tests__/`
- [x] `npm run test:auth` — **10** Jest tests for errors, token, cross-app helpers

### Milestone 10 Extra — API-042 + FE-019

- [x] Spec: `specs/10_SPECS_EXTRA.md`
- [x] `test_suppliers.py` + `test_incidents.py` (12 tests); isolated `SUPPLIERS_DB_PATH`
- [x] Coverage ≥ **60%** on supplier/incident modules (models **83%**, `routes/suppliers` **72%**, `app/incidents/analysis` **90%**)
- [x] `uis/talent-pipeline-tracker/__tests__/` — validation + labels (10 Jest tests, **~86%** line coverage)
- [x] `npm run test:tracker`; `TESTING.md` updated

### Milestone 11 — Centralized Incident Manager

- [x] Spec: `specs/11_SPECS.md`; context: `context/11_CONTEXT.md`
- [x] Incident CRUD API (`/api/incidents`, status lifecycle, summary)
- [x] `csv_validation.py` extracted; `scripts/seed_incidents.py` (94 valid rows, idempotent)
- [x] `packages/shared/incidents/` — constants, labels, lifecycle helpers
- [x] Backoffice: register, list (filters + status updates), summary pages + BFF

### Milestone 12 — Error handling hardening

- [x] Spec: `specs/12_SPECS.md` (audit-driven remediation)
- [x] FastAPI: sanitized validation errors; password-reset delivery rollback; safe route error messages
- [x] Shared `packages/shared/api/errors.ts` — `sanitizeApiDetail`, `toUserFacingMessage`
- [x] BFF routes (23): scoped `runBffHandler`, sanitized proxy responses
- [x] Frontend: `ErrorState` component, retry/home CTAs, `error.tsx` / `global-error.tsx` in internal apps
- [x] API client libs: network/JSON try/catch wrappers
- [x] Scripts: `seed_incidents.py`, `analyze.py` — defensive I/O with `sys.exit(1)`
- [x] Docs: READMEs, `TESTING.md`, `scripts/README.md` — M12 paths, exit codes, validation behaviour

### Milestone 5.5 — Inventory management (ORM & dual database)

- [x] Spec: `specs/05.5_SPECS.md`; context: `context/05.5_CONTEXT.md`
- [x] `services/api/inventory/` — SQLModel models, Pydantic schemas, stock service, `/inventory` router
- [x] Dual store: TinyDB auth unchanged; inventory on Postgres (Supabase) or local SQLite via `SUPABASE_DATABASE_URL`
- [x] `current_stock` computed from deliveries − consumptions; outbound rejects insufficient stock (exact 400 message)
- [x] `seed_inventory.py` — 6 supplies, ≥4 deliveries, ≥3 consumptions; `--reset` for local rebuild
- [x] `tests/test_inventory.py` — I1–I9 plus duplicate SKU, unknown supply, schema edges (in-memory SQLite)
- [x] Backoffice UI (`specs/05.5_SPECS_FRONT.md`) — catalogue, vendor delivery, clinical consumption, supply movements
- [x] BFF at `app/api/inventory/*` via `INVENTORY_API_URL`; client helpers in `lib/api/inventory.ts` (`authFetch` only)
- [x] Nav: **Supplies** (`/inventory/products`), **Movements** (`/inventory/orders`)

### Milestone 13 — Docker Compose

- [x] Spec: `specs/13_SPECS.md`
- [x] `uis/Dockerfile` + `uis/start.sh` — website `:3000` and backoffice `:3001` (`next dev`, hot reload)
- [x] `services/Dockerfile` — Python 3.12 + uv, `requirements.txt`, Uvicorn `--reload` on `:8000`
- [x] Root `docker-compose.yml` — services `ui` and `api` on network `healthcore`; BFF URLs `http://api:8000`
- [x] Root `.env.example` (secrets stay in gitignored `.env`)
- [x] `GET /health` for Compose probes (not `/openapi.json`)

### Telemetry Plan (design)

- [x] Spec context: `context/13_CONTEXT.md`
- [x] `docs/telemetry/telemetry-plan.md` — mandatory CONTEXT metrics + broad backoffice catalogue
- [x] `docs/telemetry/event-schemas.json` — envelope + 5 mandatory + 11 identified event schemas (16 total, including `web_vital_recorded`)

### Milestone 6.5 — Telemetry capture (frontend)

- [x] Spec: `specs/06.5_FE_TELEM_SPECS.md`; context: `context/06.5_CONTEXT.md`
- [x] FastAPI stub `POST /telemetry/events` — envelope validation, `{ received: N }`, no DB
- [x] `uis/backoffice/lib/telemetry/` — queue, 10s/20 batch, sendBeacon, retry, `track()`
- [x] Mandatory CONTEXT events + auth, latency, errors, page views, Web Vitals
- [x] `NEXT_PUBLIC_TELEMETRY_ENDPOINT` / `TELEMETRY_ENDPOINT`

### Milestone 6.5 — Telemetry storage (backend)

- [x] Spec: `specs/06.5_BE_TELEM_SPECS.md`
- [x] `telemetry_events` on the inventory SQL engine; bulk `add_all`; one commit per batch
- [x] Loose `{ events: [...] }` parse; per-item `TelemetryEvent.model_validate`; HTTP 200 `{ received, stored, rejected }`
- [x] Allowlisted `tags` + correlation keys; no PHI keys; mapping in `docs/telemetry/telemetry-plan.md` §3.4

### Milestone 6.5 — Telemetry operational report

- [x] Spec: `specs/06.5_TELEM_REPORT_SPECS.md`
- [x] `telemetry/analysis.py` — SQL window load, Pandas group/agg, `build_report`
- [x] `GET /telemetry/report` — auth, last-7-days default, 60s in-memory cache
- [x] Backoffice `/telemetry` + BFF `/api/telemetry/report` (tables only)

### Data pipelines — Monthly Clinic Supply Performance (design)

- [x] Spec context: `context/06.5_PIPELINE_CONTEXT.md`
- [x] `data/pipelines/PIPELINE_DESIGN.md` — extract/transform/load, `reporting.monthly_clinic_supply_performance`, Prefect mapping, `services/api/reporting/` endpoints

### Data pipelines — Monthly Clinic Supply Performance (implementation)

- [x] Prefect 3 flow `monthly_clinic_supply_performance` — tasks `extract_month`, `transform_clinic_month` (cached 6h), `load_clinic_month` (upsert), optional `write_eval_snapshot` (`return_state=True`)
- [x] CLI: `python data/pipelines/pipeline.py` — schedule 06:00 UTC on the 1st
- [x] Destination `reporting.monthly_clinic_supply_performance` + `reporting.pipeline_runs` (never writes `telemetry_events`)
- [x] `services/api/reporting/` — `GET` KPIs, `GET` latest run, `POST` trigger; imports from `data/pipelines/`
- [x] Additive `unit_cost` / `total_cost` on `inbound_order_created` allowlist (not `telemetry/analysis.py`)

### Data pipelines — Subflows, tests, board dashboard (spec)

- [x] Spec: `specs/06.5_PREFECT_SPECS.md` — named subflows, `tests/pipelines/test_pipeline.py`, keep CLI, backoffice `/reporting`

### Data pipelines — Subflows, tests, board dashboard (implementation)

- [x] Named subflows: `extract_monthly_clinic_supply_events`, `transform_monthly_clinic_supply_kpis`, `load_monthly_clinic_supply_performance`, `snapshot_monthly_clinic_supply_eval` (`return_state=True`)
- [x] CLI unchanged: `uv run python data/pipelines/pipeline.py [--month-start YYYY-MM-DD]`
- [x] Isolated transform tests: `tests/pipelines/test_pipeline.py` (hand-calc Austin North 205 USD; no DB)
- [x] Root `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests/pipelines"]`, `pythonpath = ["."]`
- [x] Backoffice `/reporting` — four CONTEXT KPI titles, clinic labels, BFF `/api/reporting/*`; nav **Clinic supply**
- [x] Overlap lock documented: `begin_pipeline_run` closes leftover `running` rows (`PIPELINE_DESIGN.md` §6 / §7)
- [x] Optional Prefect Cloud: `PREFECT_API_KEY` / `PREFECT_API_URL` in gitignored `.env`; CLI uses repo `.prefect/` (tests stay ephemeral)

### Nightly export worker (7.1)

- [x] Spec: `specs/07.1_CRON_SPECS.md`
- [x] `scripts/nightly_export.py` — yesterday UTC (or `TARGET_DATE`); CSV backup; pipeline subprocess `--no-sample`
- [x] `services/jobs/job_runner.py` + `schema.sql` — `job_runs` (`pending` → `processing` → `completed`/`failed`); lock = `processing`
- [x] Trigger: `deploy/nightly.crontab` (`5 2 * * *` UTC) and Compose service `nightly` (`scripts/nightly_loop.py`) — not FastAPI
- [x] Tests: `tests/jobs/` (lock, duplicate skip, failed does not stay `processing`)

### Sales forecast (7.2)

- [x] Spec: `specs/07.2_TIMESERIES_SPECS.md`; context: `context/07_CONTEXT.md`
- [x] `data/process/sales_forecast.py` — consolidated `revenue_usd`, causal lags/rolls, 8/2 split, train-only scaler
- [x] `scripts/forecast_sales.py` — XGBoost (`random_state=42`); MSE / PSI / Gini / K2 on 2024–2025
- [x] Plot `data/eval/sales_forecast_test.png` (actual vs pred ± train residual band)
- [x] Tests: `tests/pipelines/test_sales_forecast.py` (split + causal features)

### Sales forecast evaluation (7.3)

- [x] Spec: `specs/07.3_EVALUATION_SPECS.md`
- [x] `data/process/sales_forecast_eval.py` — 5-fold prefix-safe `TimeSeriesSplit` on 2016–2023; MAE/RMSE mean±std
- [x] Learning curve `data/eval/sales_forecast_learning_curve.png`; report `data/eval/evaluation_report.md`
- [x] Tests: `tests/pipelines/test_sales_forecast_cv.py` (chronological folds)

### Desk knowledge RAG (7.5)

- [x] Spec: `specs/07.5_RAG_SPECS.md`; context: `context/07.5_RAG_CONTEXT.md`
- [x] Corpus in `docs/company-knowledge-base/`; Qdrant collection `healthcore_knowledge`
- [x] `setup()` / `embed()` in `data/process/rag.py`; `retrieve()` / `generate_answer()` / `query()` in `data/pipelines/rag.py`
- [x] `POST /knowledge/query` + backoffice `/knowledge` (Desk knowledge)
- [x] Tests: `tests/pipelines/test_rag.py`; Recall@3 via `scripts/eval_rag_recall.py`
- [x] Design: `docs/rag/rag-design.md`

### Desk agent graph (7.6)

- [x] Spec: `specs/07.6_LANGGRAPH_SPECS.md`; same CONTEXT as 7.5
- [x] Compiled LangGraph in `services/api/agent/` — `DeskAgentState`, five named nodes, `MemorySaver`
- [x] Nodes call `retrieve()` and `generate_answer(question, context)` separately; no `query()` in a node
- [x] Conditional edges: empty question → `reject`; empty retrieve → `refuse` (`NO_INFORMATION`)
- [x] Traces: `data/eval/agent_traces/{run_id}.json`; `POST /agent/query` + `GET /agent/traces/{run_id}`
- [x] `POST /knowledge/query` unchanged
- [x] Tests: `tests/pipelines/test_agent_graph.py` (path + Medicare grounding); `test_rag.py` still required

### Desk agent incident tool (7.7)

- [x] Spec: `specs/07.7_LANGGRAPH_TOOL_SPECS.md`
- [x] Read-only in-process lookup via `get_incident` / `list_incidents` (5s timeout)
- [x] `classify` routes `rag` / `incident` / `both` from the question; no user-selected source
- [x] Fallback: `I couldn't confirm that ticket's status right now`
- [x] Traces include `path`, `sources_used`, `incident_ids`, `incident_error`
- [x] Routing evals in `tests/pipelines/test_agent_graph.py`; `test_rag.py` still required
- [x] Incident HTTP stays JWT-protected; the tool takes no token

### Desk agent inventory lookup (7.7 stretch)

- [x] Spec: `specs/07.7_TOOL_STRETCH_SPECS.md`
- [x] Separate read-only tool via `list_supplies` / `get_supply` (5s timeout)
- [x] `classify` adds `inventory` / `inventory_rag`; ticket path unchanged
- [x] Fallback: `I couldn't confirm that supply's stock right now`
- [x] Traces include `supply_skus` / `inventory_error`
- [x] `GET /inventory/products` stays JWT-protected; the tool takes no token

### HealthCore MCP server (7.8)

- [x] Spec: `specs/07.8_MCP_SERVER_SPECS.md`
- [x] Streamable HTTP server `mcps/healthcore/` on port 8100 (`mcpauth` resource-server + PRM)
- [x] Incident tools call the existing manager; `incidents_update_status` uses `update_incident_status` only
- [x] `inventory_query` reads; `inventory_mutate` always errors `inventory_read_only`
- [x] Desk agent `lookup_incident` / `lookup_inventory` go through `langchain-mcp-adapters` (no manager import in `agent/`)
- [x] Tests: `tests/pipelines/test_agent_graph.py` (routing + `agent_incidents_via_mcp` + `mcp_inventory_mutate_rejected`); `test_rag.py` still required
- [x] `npm run dev` starts the MCP server on port 8100 alongside the other apps

### Desk-agent memory (8.5)

- [x] Spec: `specs/08.5_MEMORY_SPECS.md`; context: `context/08_CONTEXT.md`
- [x] TinyDB `items` + `decisions` in `services/api/agent_memory.json` (`AGENT_MEMORY_DB_PATH`); not Qdrant / `healthcore_knowledge`
- [x] Same compiled graph: `resolve_memory` then `propose_memory`; one pending proposal per JWT user
- [x] PHI scan (HIPAA + UK GDPR) before show and before consolidate; Patient Johnson style is a visible refusal
- [x] Classifier `approve` | `reject` | `edit` | `unclear`; unclear/expired never write `items`
- [x] Tests: `tests/pipelines/test_agent_memory.py`; evidence: `data/eval/memory_cycles.md`; `test_agent_graph.py` + `test_rag.py` still required

### Desk-agent harness (8.6)

- [x] Spec: `specs/08.6_GUARDRAILS_SPECS.md`; context: `context/08.6_CONTEXT.md`
- [x] Same compiled graph: `guard_input` / `guard_output`; isolate RAG text; rewrite `SYSTEM_PROMPT` as Claire’s compliance assistant
- [x] Stacked layers (input + isolate + output); PHI scanned on **output**, not prompt-only
- [x] `GET /agent/guardrails/summary`; logs type/name/run_id only (no PHI)
- [x] Tests: `tests/pipelines/test_agent_guardrails.py`; evidence: `data/eval/guardrail_cases.md`

### RFP intake & routing Part 1 (9.5)

- [x] Spec: `specs/09.5_RFP_INTAKE_SPECS.md`; context: `context/09.5_CONTEXT.md`
- [x] Dedicated `rfp_intake` graph under `data/pipelines/rfp_intake/` (MarkItDown, readability, classifier, three workers, synthesizer)
- [x] SQLModel tickets/metadata/sections on the inventory Postgres engine — not TinyDB
- [x] `POST /rfp/tickets` 202 + background run; `GET` ticket + sections; CLI `scripts/run_rfp_intake.py`
- [x] Backoffice `/rfp` upload + poll; BFF `/api/rfp/*`
- [x] Tests: `tests/pipelines/test_rfp_intake.py` (formal accept, informal accept, EHR reject, missing volume, PHI redact)

### RFP response generation Part 2 (9.6)

- [x] Spec: `specs/09.6_RFP_RESPONSE_SPECS.md`; context: `context/09.5_CONTEXT.md`
- [x] Dedicated `rfp_draft` graph under `data/pipelines/rfp_draft/` (generate → evaluate → loop cap 3 → persist)
- [x] `part2_handoff_json` on the same ticket row; statuses `drafting` / `under_evaluation` / `needs_human_review`
- [x] `POST /rfp/tickets/{id}/draft` 202 + background run; GET ticket/sections include drafts + evals; CLI `scripts/run_rfp_draft.py`
- [x] Backoffice `/rfp` generate + poll + provisional badge
- [x] Tests: `tests/pipelines/test_rfp_draft.py` (revenue generator, relevance fail, `baa-us`, PHI, persist)

### RFP approval and completion Part 3 (9.7)

- [x] Spec: `specs/09.7_RFP_APPROVAL_SPECS.md`; context: `context/09.5_CONTEXT.md`
- [x] Dedicated `rfp_approval` graph: one SqliteSaver thread per department, parent join with no interrupt
- [x] Decisions `approve` / `request_changes` / `reject`; cap 3; CONTEXT triggers `phi-detected`, `baa-dpa-mismatch`, `capacity-vs-population`
- [x] Statuses `waiting_for_approval` and `done`; `final_document_json` after all three owners approve
- [x] `POST /rfp/tickets/{id}/approvals` 202 and `POST .../approvals/{department_id}`; backoffice `/rfp` decisions
- [x] Tests: `tests/pipelines/test_rfp_approval.py`; smoke: `scripts/run_rfp_approval_e2e.py`

### SSE ticket notices (10.5)

- [x] Spec: `specs/10.5_SSE_SPECS.md`; context: `context/10.5_CONTEXT.md`
- [x] `GET /rfp/events` pushes `rfp_ticket_created` from `persist_complete` after metadata is stored, while the payload status is still `analyzing`
- [x] `GET /rfp/tickets` returns the newest 20 with the same seven ticket fields so a missed event is recovered on reconnect
- [x] Backoffice `/` shows institution, country, and program type, streams `/api/rfp/events` with `authFetch`, and dedupes on `ticket_id`
- [x] Tests: `tests/pipelines/test_rfp_sse.py`

### Desk chat WebSocket (10.6)

- [x] Spec: `specs/10.6_WEBSOCKET_SPECS.md`; context: `context/10.6_CONTEXT.md`
- [x] `WS /agent/chat` streams `token_chunk` (`token`, `sequence`) for `compliance_assistant`; `interrupt_requested` aborts the HTTP stream and keeps the partial reply
- [x] One producer on `chat.<session_id>` fans out to every socket; reconnect sends `session_snapshot`
- [x] Desk page `/knowledge` appends each token and sends `interrupt_requested` while a reply is in progress
- [x] Tests: `tests/pipelines/test_agent_ws.py`

### OWASP audit and host hardening (11.5)

- [x] Spec: `specs/11.5_OWASP_SPECS.md`; report: `docs/security/11.5_OWASP_AUDIT.md`
- [x] Root SSH off; firewall default-deny; Qdrant and API published on `127.0.0.1`; API image is non-root
- [x] OpenAPI docs off unless `HEALTHCORE_EXPOSE_DOCS=1`; compliance agent refuses an instruction to reveal a patient identifier
- [x] Thirty findings (10 categories × backend, frontend, agentic). No open critical item

### Secure practices for AI (12)

- [x] Spec: `specs/12_NIST_SPECS.md`; inventory: `docs/security/12_NIST/README.md`; report: `docs/security/12_NIST/REPORT.md`
- [x] RFP upload is data: instruction override skips the model; untrusted markers; model `is_rfp: true` cannot override fallback `false`
- [x] Output guard refuses the embedded medication instruction with the existing leak refusal
- [x] Desk traces and the eight fixtures record the action only (no question or answer text)
- [x] `POST /agent/query` limited to 10 requests / 60 seconds per user, then HTTP 429. Chat WebSocket and `POST /knowledge/query` stay unlimited

## Planned next

- Live API integrations for backoffice operations dashboard
- Agent implementations under `agents/`
- HealthCore central API
