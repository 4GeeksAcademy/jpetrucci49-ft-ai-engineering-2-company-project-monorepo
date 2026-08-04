# HealthCore Monorepo — Progress

_Last updated: Milestone 5 Phase 2 — incident analysis platform integration_

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

## In progress

- [ ] Live API integrations for backoffice operations dashboard (future milestone)

## Planned next

- Agent implementations under `agents/`
- Executive KPI dashboard
- HealthCore central API
