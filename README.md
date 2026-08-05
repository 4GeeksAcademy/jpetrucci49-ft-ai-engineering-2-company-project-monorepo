# HealthCore Monorepo

HealthCore project workspace containing:

- **Next.js applications** under `uis/` (public website, operations, talent pipeline tracker)
- **FastAPI backend** under `services/api/` (incident analysis, supplier directory)
- TypeScript business logic in `src/utils`
- Agent infrastructure (`memory-bank/`, `AGENTS.md`, `.agents/`, `skills/`)
- Vitest unit tests in `tests/utils`

## Quick Start — All applications

From the repository root:

```bash
npm install
npm run dev
```

This starts every frontend and the API concurrently:

| Service | URL | Purpose |
| --- | --- | --- |
| Application hub | http://localhost:4173 | Links to all apps |
| Public website | http://localhost:3000 | Bilingual corporate site + patient enquiry |
| Operations | http://localhost:3001 | Billing, clinical, CME dashboards |
| Utility tester | http://localhost:3001/utilities | M2 function manual runner |
| Incident analysis | http://localhost:3001/incidents | CSV upload + summary (M5) |
| Talent pipeline tracker | http://localhost:3002 | Recruitment pipeline (M3) |
| HealthCore API | http://localhost:8000 | FastAPI — incidents, suppliers (M5/M6) |
| API docs | http://localhost:8000/docs | OpenAPI (Swagger) |

Copy `.env.example` to `.env.local` in each `uis/*` app if you need custom cross-app URLs.

### Individual apps

```bash
npm run dev:website      # port 3000
npm run dev:backoffice   # port 3001
npm run dev:tracker      # port 3002
npm run dev:hub          # port 4173 (links only)
npm run dev:api          # port 8000 (FastAPI)
npm run dev:uis          # frontends only (no hub or API)
```

## HealthCore API (`services/api/`)

Python 3.12+ service managed with [uv](https://docs.astral.sh/uv/). See [`services/api/README.md`](services/api/README.md) for endpoints and environment variables.

```bash
cd services/api
uv sync
uv run uvicorn app.main:app --reload --port 8000   # or: npm run dev:api from repo root
```

### Supplier directory seed (Milestone 6)

Load the initial 15 suppliers into TinyDB (idempotent — safe to run more than once):

```bash
cd services/api
uv run seed
```

| Run | Expected output |
| --- | --- |
| First run (empty database) | `15 supplier(s) inserted (15 total in database)` |
| Later runs | `0 supplier(s) inserted (15 total in database)` |

Data is stored in `services/api/suppliers.json` (gitignored). Override the path with `SUPPLIERS_DB_PATH` — see `services/api/.env.example`.

To re-seed from scratch:

```bash
cd services/api
rm -f suppliers.json
uv run seed
```

### Incident analysis CLI (Milestone 5)

From the repository root:

```bash
uv sync
uv run python scripts/analyze.py scripts/incidents.csv
```

## Production

```bash
npm run build
npm start
```

Builds all three Next.js apps, then serves them on ports 3000–3002.

## TypeScript utilities (Milestone 2)

```bash
npm run typecheck
npm test
npm run utils:playground
```

Business logic lives in `src/utils/` and is imported by `uis/backoffice` — never duplicated.

## Development Workflow

- Root quality gates: `npm run typecheck`, `npm test`
- All apps: `npm run lint:apps`
- Single app: `cd uis/<app> && npm run lint && npm run build`

## Repository Areas

- `memory-bank/` — Agent session context
- `src/` — M2 TypeScript utilities
- `tests/` — Vitest suites and fixtures
- `uis/website/` — Public Next.js site (M1 migration)
- `uis/backoffice/` — Internal operations dashboard (M4)
- `uis/talent-pipeline-tracker/` — Recruitment UI (M3)
- `services/api/` — FastAPI backend (incidents M5, supplier directory M6)
- `scripts/` — Python CLI utilities and test data
- `context/` — Milestone company scenarios (programme-assigned)
- `public/index.html` — Local dev application hub

## Agent infrastructure

See root `AGENTS.md` for session startup files, pre-commit workflow, and protected paths.

## Legacy note

The original static HTML site (`index.html`, `application.html`, `utility-test.html`) has been migrated to Next.js apps under `uis/`. The `assets/` folder remains for reference artifacts; Tailwind v3 build scripts are retained for historical compatibility only.
