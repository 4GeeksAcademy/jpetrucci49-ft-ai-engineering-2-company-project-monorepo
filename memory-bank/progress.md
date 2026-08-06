# HealthCore Monorepo — Progress

_Last updated: Milestone 6 complete — supplier directory API + backoffice UI_

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

## In progress

- [ ] Live API integrations for backoffice operations dashboard (future milestone)

## Planned next

- Agent implementations under `agents/`
- Executive KPI dashboard
- HealthCore central API
