# HealthCore API

FastAPI service for internal HealthCore Digital tools:

- **M5** — Patient incident CSV analysis (backoffice `/incidents`)
- **M6** — Supplier directory (TinyDB + Pydantic; REST routes and UI in progress)

## Stack

| Item | Value |
| --- | --- |
| Framework | FastAPI |
| Python | 3.12+ |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Default port | `8000` |
| Supplier storage | TinyDB (`suppliers.json`, gitignored) |

## Setup

```bash
cd services/api
uv sync
cp .env.example .env   # optional — CORS, SUPPLIERS_DB_PATH
```

## Run (development)

From `services/api/`:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

From the repository root:

```bash
npm run dev:api
```

## Supplier directory (Milestone 6)

Pydantic models live in `models.py`. TinyDB is initialised in `database.py`. Seed data matches `context/06_CONTEXT.md`.

### Seed the database

```bash
cd services/api
uv run seed
```

| Run | Expected output |
| --- | --- |
| First run (empty `suppliers.json`) | `Seeder finished: 15 supplier(s) inserted (15 total in database).` |
| Subsequent runs | `Seeder finished: 0 supplier(s) inserted (15 total in database).` |

The seeder is **idempotent** — it skips suppliers already stored (matched by `name` + `country`). `0 inserted` with `15 total` means the directory is already loaded, not a failure.

Reset and re-seed:

```bash
rm -f suppliers.json
uv run seed
```

Optional env var `SUPPLIERS_DB_PATH` overrides the default database file path (see `.env.example`).

Specs: `specs/06_SPECS_DATA.md`, `specs/06_SPECS_SEEDER.md`.

## Incident analysis (Milestone 5)

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/incidents/analyze` | Upload CSV (`multipart/form-data`, field `file`) → JSON summary |
| `GET` | `/api/incidents/results/export` | Download last analysis as `results.csv` |

## Shared analysis logic

Business rules live in `app/incidents/analysis.py`. The CLI script `scripts/analyze.py` imports the same module — do not duplicate validation logic elsewhere.

## Result storage

The last successful analysis is held **in memory** for the current API process. Restarting the server clears it until a new CSV is uploaded. Production would use persistent storage.

**PHI policy:** Raw CSV content and row-level fields (`patient_id`, `description`) are never stored, logged, or returned — only aggregate metrics.

## CORS

Set `CORS_ORIGINS` (comma-separated) for direct browser access to FastAPI. The backoffice normally proxies via Next.js route handlers (`uis/backoffice/app/api/incidents/`), so CORS is not required for the standard upload flow.

Defaults allow `localhost:3001` and Codespaces URLs (`*.github.dev`). See `.env.example`.

## Architecture note

```
Browser → backoffice :3001 /api/incidents/*
       → Next.js route handler (server-side)
       → FastAPI :8000 /api/incidents/*
       → app/incidents/analysis.py (shared with scripts/analyze.py)
```

## Manual test

```bash
curl -X POST http://localhost:8000/api/incidents/analyze \
  -F "file=@../../scripts/incidents.csv"

curl -OJ http://localhost:8000/api/incidents/results/export
```

Expected totals for `scripts/incidents.csv`: 100 total, 94 valid, 6 invalid, average satisfaction 3.58.

## Project layout (M6 target)

```text
services/api/
  app/main.py          ← FastAPI app (incidents today; suppliers routes pending)
  models.py            ← Supplier Pydantic models
  database.py          ← TinyDB initialisation
  seed.py              ← Initial supplier data (`uv run seed`)
  routes/              ← Supplier REST endpoints (planned)
  suppliers.json       ← TinyDB file (gitignored, created by seed)
```
