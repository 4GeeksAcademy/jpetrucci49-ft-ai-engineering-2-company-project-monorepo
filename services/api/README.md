# HealthCore API

FastAPI service for internal HealthCore Digital tools:

| Milestone | Feature | Backoffice route |
| --- | --- | --- |
| M5 | Patient incident CSV analysis | `/incidents` |
| M6 | Supplier directory (TinyDB) | `/suppliers` |
| M7 | JWT auth + route protection | — |
| M8 | Frontend auth (login, guards, BFF token forward) | `/login`, `/account/profile` |
| M9 | Password reset + change (API) | `/forgot-password`, `/reset-password`, `/account/change-password` (frontend in M9 phase 2) |

## Stack

| Item | Value |
| --- | --- |
| Framework | FastAPI · Python 3.12+ · [uv](https://docs.astral.sh/uv/) |
| Port | `8000` |
| Storage | TinyDB — `suppliers.json`, `auth.json` (both gitignored) |
| Auth | PyJWT (HS256) + libpass bcrypt |

## Quick start

```bash
cd services/api
uv sync
cp .env.example .env          # set JWT_SECRET (required)
uv run seed                   # load 15 suppliers (idempotent)
uv run --env-file .env uvicorn app.main:app --reload --port 8000
```

From the repo root: `npm run dev:api` (loads `services/api/.env`).

OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

The API fails fast at startup if `JWT_SECRET` is missing, or if password-reset / email env vars are incomplete (see below).

## Authentication (M7)

Stateless bearer JWT. Public routes: `POST /users`, `POST /auth/login`, password recovery routes (M9), and docs. Everything else requires `Authorization: Bearer <token>`.

| Method | Path | Access |
| --- | --- | --- |
| `POST` | `/users` | Public — register user + profile |
| `POST` | `/auth/login` | Public — OAuth2 form (`username` = email) |
| `POST` | `/auth/forgot-password` | Public — request reset link (always **200**) |
| `POST` | `/auth/reset-password` | Public — set new password with reset token |
| `POST` | `/auth/change-password` | Authenticated — change password with current password |
| `GET` | `/auth/me` | Authenticated |
| `GET/PUT` | `/profiles/me` | Owner |
| `GET` | `/users` | Admin |
| `GET/PUT/DELETE` | `/users/{id}` | Self or admin |

All supplier and incident endpoints require a valid token when called on FastAPI directly. Internal apps attach the token via `authFetch` and the Next.js BFF forwards the `Authorization` header.

### Auth smoke test

```bash
BASE=http://127.0.0.1:8000

curl -s -X POST "$BASE/users" -H 'Content-Type: application/json' \
  -d '{"email":"ops@example.com","password":"securepass123","name":"Ops User"}'

TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -d 'username=ops@example.com&password=securepass123' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s "$BASE/suppliers" -H "Authorization: Bearer $TOKEN"
```

**First admin:** edit `auth.json` while the API is stopped, set `"role": "admin"`, restart. Spec: `specs/07_SPECS.md`.

## Password recovery and change (M9)

Spec: `specs/09_SPECS_BACK.md`.

Reset tokens are opaque, single-use, and stored hashed in TinyDB (`password_reset_tokens` table in `auth.json`). The `/auth/forgot-password` endpoint always returns **200** with the same message — it never reveals whether an email is registered.

### Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `RESET_TOKEN_EXPIRE_MINUTES` | No | `30` | Reset link lifetime (15–60) |
| `PASSWORD_RESET_URL` | **Yes** | — | Frontend reset page, e.g. `http://localhost:3001/reset-password` |
| `RESEND_API_KEY` | **Yes** | — | [Resend](https://resend.com/) API key |
| `RESEND_FROM_EMAIL` | **Yes** | — | Verified or onboarding sender |

Create a free [Resend](https://resend.com/) account, copy the API key, and use Resend’s onboarding sender (e.g. `onboarding@resend.dev`) until you verify a custom domain.

### Password reset smoke test

```bash
BASE=http://127.0.0.1:8000

curl -s -X POST "$BASE/auth/forgot-password" \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@example.com"}'

# Use token from email:
curl -s -X POST "$BASE/auth/reset-password" \
  -H 'Content-Type: application/json' \
  -d '{"token":"<token-from-email>","new_password":"newsecurepass123"}'

# Change password while logged in:
curl -s -X POST "$BASE/auth/change-password" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"current_password":"newsecurepass123","new_password":"anothersecurepass123"}'
```

## Supplier directory (M6)

Models in `models.py`, TinyDB in `database.py`, seed data from `context/06_CONTEXT.md`.

```bash
uv run seed                              # from services/api/
uv run --directory services/api seed     # from repo root
```

| Run | Expected |
| --- | --- |
| First run | `15 supplier(s) inserted` |
| Later runs | `0 inserted` with `15 total` — already loaded |

Reset: `rm -f suppliers.json && uv run seed`. Override path with `SUPPLIERS_DB_PATH` (see `.env.example`).

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/suppliers` | Register supplier |
| `GET` | `/suppliers` | List; optional `?country=` and `?category=` |
| `GET` | `/suppliers/{id}` | Detail |
| `PATCH` | `/suppliers/{id}/rate` | Update `monthly_rate` |
| `PATCH` | `/suppliers/{id}/status` | Set `active` or `suspended` |
| `DELETE` | `/suppliers/{id}` | Remove supplier |

All supplier routes require a bearer token. UI: `uis/backoffice/app/suppliers/`.

Specs: `specs/06_SPECS_*.md`.

## Incident analysis (M5)

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/incidents/analyze` | Upload CSV → JSON summary |
| `GET` | `/api/incidents/results/export` | Download last analysis as CSV |

Business rules live in `app/incidents/analysis.py` (shared with `scripts/analyze.py`). Last result is **in-memory** — restart clears it.

**PHI policy:** Never store, log, or return `patient_id` or `description` — aggregates only.

```bash
curl -X POST http://127.0.0.1:8000/api/incidents/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@../../scripts/incidents.csv"
```

Expected for `scripts/incidents.csv`: 100 total, 94 valid, 6 invalid, avg satisfaction 3.58.

## CORS and architecture

CORS defaults cover `localhost:3001` and Codespaces (`*.github.dev`). The backoffice normally proxies server-side, so CORS is not required for standard UI flows.

```text
Browser → backoffice :3001 /api/{incidents,suppliers}/*
       → Next.js BFF (server-side)
       → FastAPI :8000
```

## Project layout

```text
services/api/
  app/main.py       ← FastAPI app
  auth/             ← JWT module (M7) + password reset (M9)
  routes/           ← auth, users, profiles, suppliers
  app/incidents/    ← analysis module + router (M5)
  models.py         ← Supplier Pydantic models
  database.py       ← Supplier TinyDB
  seed.py           ← Supplier seeder
  auth.json         ← Users + profiles (gitignored)
  suppliers.json    ← Suppliers (gitignored)
```
