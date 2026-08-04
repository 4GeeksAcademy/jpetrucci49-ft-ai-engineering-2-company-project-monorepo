# HealthCore API

FastAPI service for internal HealthCore Digital tools. Phase 2 exposes patient incident CSV analysis for the backoffice Patient Experience workflow.

## Stack

| Item | Value |
| --- | --- |
| Framework | FastAPI |
| Python | 3.12+ |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Default port | `8000` |

## Setup

```bash
cd services/api
uv sync
```

Copy environment variables if needed:

```bash
cp .env.example .env
```

## Run (development)

From `services/api/`:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

From the repository root (via npm):

```bash
npm run dev:api
```

## Endpoints

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

Set `CORS_ORIGINS` (comma-separated) for allowed browser origins. Default: `http://localhost:3001` (backoffice dev server).

## Manual test

```bash
curl -X POST http://localhost:8000/api/incidents/analyze \
  -F "file=@../../data/raw/incidents.csv"

curl -OJ http://localhost:8000/api/incidents/results/export
```

Expected totals for `data/raw/incidents.csv`: 100 total, 94 valid, 6 invalid, average satisfaction 3.58.
