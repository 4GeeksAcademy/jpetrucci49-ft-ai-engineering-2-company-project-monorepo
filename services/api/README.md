# HealthCore API

FastAPI service for internal HealthCore Digital tools:

- **M5** — Patient incident CSV analysis (backoffice `/incidents`)
- **M6** — Supplier directory (TinyDB + Pydantic; REST API + backoffice UI at `/suppliers`)
- **M7** — JWT authentication and route protection (TinyDB users + profiles)

## Stack

| Item | Value |
| --- | --- |
| Framework | FastAPI |
| Python | 3.12+ |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Default port | `8000` |
| Supplier storage | TinyDB (`suppliers.json`, gitignored) |
| Auth storage | TinyDB (`auth.json`, gitignored) |
| Tokens | PyJWT (HS256) + libpass bcrypt |

## Setup

```bash
cd services/api
uv sync
cp .env.example .env   # required — set JWT_SECRET before starting the API
```

`JWT_SECRET` is mandatory. The API fails fast at startup if it is missing.

## Run (development)

From `services/api/`:

```bash
uv run --env-file .env uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

From the repository root:

```bash
npm run dev:api
```

(`dev:api` loads `services/api/.env` — create it from `.env.example` first.)

## Authentication (Milestone 7)

Stateless bearer JWT auth. Register publicly, log in, then send `Authorization: Bearer <token>` on protected routes.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/users` | Public | Register user + profile → **201** |
| `POST` | `/auth/login` | Public | OAuth2 form (`username` = email) → JWT |
| `GET` | `/auth/me` | Protected | Email, role, linked profile |
| `GET` | `/profiles/me` | Protected | Owner profile |
| `PUT` | `/profiles/me` | Protected | Update name, phone, address |
| `GET` | `/users` | Admin | List users |
| `GET/PUT/DELETE` | `/users/{id}` | Self or admin | User CRUD |

All supplier and incident endpoints require a valid token. The backoffice BFF does not send tokens yet — expect **401** from those proxies until a follow-up milestone.

### Quick auth test

```bash
# Register
curl -s -X POST http://localhost:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@example.com","password":"securepass123","name":"Ops User"}'

# Login (OAuth2 form)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d 'username=ops@example.com&password=securepass123' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Protected route
curl -s http://localhost:8000/suppliers -H "Authorization: Bearer $TOKEN"
```

Specs: `specs/07_SPECS.md`.

## Supplier directory (Milestone 6)

Pydantic models live in `models.py`. TinyDB is initialised in `database.py`. Seed data matches `context/06_CONTEXT.md`.

### Seed the database

From the repository root:

```bash
uv run --directory services/api seed
```

Or from `services/api/`:

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
cd services/api
rm -f suppliers.json
uv run seed
```

Optional env var `SUPPLIERS_DB_PATH` overrides the default database file path (see `.env.example`).

Specs: `specs/06_SPECS_DATA.md`, `specs/06_SPECS_SEEDER.md`, `specs/06_SPECS_ENDPOINTS.md`, `specs/06_SPECS_FRONTEND.md`.

The backoffice UI lives at `uis/backoffice/app/suppliers/` (not `uis/application/`).

### Supplier endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/suppliers` | Register supplier → `201` + `Supplier` |
| `GET` | `/suppliers` | List all; optional `?country=USA\|UK` and `?category=<slug>` |
| `GET` | `/suppliers/{id}` | Supplier detail |
| `PATCH` | `/suppliers/{id}/rate` | Update `monthly_rate` (sets `updated_at`) |
| `PATCH` | `/suppliers/{id}/status` | Set `active` or `suspended` |
| `DELETE` | `/suppliers/{id}` | Remove supplier → `204` |

```bash
curl -s http://localhost:8000/suppliers -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/suppliers?country=USA&category=clinical_software" -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8000/suppliers/1 -H "Authorization: Bearer $TOKEN"
```

Unauthenticated requests return **401**.

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

Requires a bearer token (see [Authentication](#authentication-milestone-7)):

```bash
curl -X POST http://localhost:8000/api/incidents/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@../../scripts/incidents.csv"

curl -OJ http://localhost:8000/api/incidents/results/export \
  -H "Authorization: Bearer $TOKEN"
```

Expected totals for `scripts/incidents.csv`: 100 total, 94 valid, 6 invalid, average satisfaction 3.58.

## Project layout

```text
services/api/
  app/main.py          ← FastAPI app (auth, incidents, suppliers)
  auth/                ← JWT auth module (M7)
  models.py            ← Supplier Pydantic models
  database.py          ← Supplier TinyDB initialisation
  seed.py              ← Initial supplier data (`uv run seed`)
  routes/              ← auth, users, profiles, suppliers
  auth.json            ← Auth TinyDB file (gitignored)
  suppliers.json       ← Supplier TinyDB file (gitignored)
```
