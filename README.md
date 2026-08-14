# HealthCore Monorepo

HealthCore project workspace containing:

- **Next.js applications** under `uis/` (public website, operations, talent pipeline tracker)
- **FastAPI backend** under `services/api/` (auth, incident analysis, supplier directory)
- TypeScript business logic in `src/utils`
- Agent infrastructure (`memory-bank/`, `AGENTS.md`, `.agents/`, `skills/`)
- Vitest unit tests in `tests/utils`

## Quick start

```bash
npm install
cd services/api && uv sync && cp .env.example .env && uv run seed && cd ../..
npm run dev
```

Set `JWT_SECRET` in `services/api/.env` (required for the API). The seed step is idempotent — safe to run again.

### Testing admin-only API behaviour

There is no admin UI for promoting users. New registrations always get `"role": "user"`. Admin-only endpoints (for example `GET /users`) are documented in [`specs/07_SPECS.md`](specs/07_SPECS.md). To exercise them locally:

1. **Start the stack** — `npm run dev` (API on `:8000`, internal apps on `:3001` / `:3002`).
2. **Register a user** — open http://localhost:3001/register (or `:3002/register`), complete the form, and confirm you can reach `/account/profile`.
3. **Stop the application** — press Ctrl+C in the terminal running `npm run dev`. The API must be stopped before editing the auth database.
4. **Promote the user to admin** — edit `services/api/auth.json`. Under `users`, find the entry for your email and set `"role": "admin"` (allowed values: `admin`, `manager`, `user`).
5. **Restart** — run `npm run dev` again.
6. **Verify** — log in with the same account (or refresh an authenticated page). `/account/profile` should show role **admin**; `GET /users` via http://localhost:8000/docs or curl should return **200** instead of **403**.

The bearer token identifies the user only; role is read from TinyDB on each request, so a fresh login is not strictly required after the edit — but restarting ensures the file change is picked up cleanly.

### Testing password recovery and change (M9)

Specs: [`specs/09_SPECS_BACK.md`](specs/09_SPECS_BACK.md) (API), [`specs/09_SPECS_FRONT.md`](specs/09_SPECS_FRONT.md) (UI).

**Prerequisites** — in `services/api/.env`:

```bash
JWT_SECRET=...
PASSWORD_RESET_URL=http://localhost:3001/reset-password   # or :3002 for tracker-only
RESET_TOKEN_EXPIRE_MINUTES=30
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=onboarding@resend.dev   # or your verified Resend sender
```

Restart the API after editing `.env`. On Resend’s free tier, reset emails usually deliver only to the address on your Resend account unless you have verified a domain.

#### UI smoke test (backoffice `:3001` or tracker `:3002`)

1. **Register or log in** — http://localhost:3001/register
2. **Forgot password** — `/login` → “Forgot your password?” → submit a registered email → confirmation appears and the form disables (same message for unknown emails)
3. **Reset via email** — open the link from your inbox → `/reset-password?token=...` → set a new password → redirect to `/login` with a success message
4. **Sign in** — use the new password
5. **Change password (logged in)** — `/account/profile` → “Change password” → `/account/change-password` → submit current + new password → success message; sign in again with the new password
6. **Reuse reset token** — repeat step 2 and complete reset once; submitting the same email link again should show an error and a link back to `/forgot-password`

Repeat on http://localhost:3002 if you use the talent tracker. Set `PASSWORD_RESET_URL` to `http://localhost:3002/reset-password` when testing that app’s email links.

#### API smoke test (curl)

See [`services/api/README.md`](services/api/README.md#password-recovery-and-change-m9) for curl examples against `:8000`.

| Service | URL | Purpose |
| --- | --- | --- |
| Application hub | http://localhost:4173 | Links to all apps |
| Public website | http://localhost:3000 | Bilingual corporate site + patient enquiry |
| Operations | http://localhost:3001 | Billing, clinical, CME dashboards |
| Utility tester | http://localhost:3001/utilities | M2 function manual runner |
| Incident analysis | http://localhost:3001/incidents | CSV upload + summary (M5) |
| Supplier directory | http://localhost:3001/suppliers | Browse and manage vendors (M6) |
| Talent pipeline tracker | http://localhost:3002 | Recruitment pipeline (M3) |
| HealthCore API | http://localhost:8000 | FastAPI — auth, incidents, suppliers (M5–M9) |
| API docs | http://localhost:8000/docs | OpenAPI (Swagger) |

### Individual apps

```bash
npm run dev:website      # port 3000
npm run dev:backoffice   # port 3001
npm run dev:tracker      # port 3002
npm run dev:hub          # port 4173 (links only)
npm run dev:api          # port 8000 (FastAPI)
npm run dev:uis          # frontends only (no hub or API)
```

Copy `.env.example` to `.env.local` in a `uis/*` app when you need custom API proxy URLs (see each app’s README).

## HealthCore API

Python 3.12+ service managed with [uv](https://docs.astral.sh/uv/). Full setup, endpoints, auth flow, and seeding: [`services/api/README.md`](services/api/README.md).

## Incident analysis CLI (Milestone 5)

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

## Development workflow

- Root quality gates: `npm run typecheck`, `npm test`
- All apps: `npm run lint:apps`
- Single app: `cd uis/<app> && npm run lint && npm run build`

## Repository areas

| Path | Purpose |
| --- | --- |
| `memory-bank/` | Agent session context |
| `src/` | M2 TypeScript utilities |
| `tests/` | Vitest suites and fixtures |
| `uis/website/` | Public Next.js site (M1) |
| `uis/backoffice/` | Internal operations dashboard (M4–M6) |
| `uis/talent-pipeline-tracker/` | Recruitment UI (M3) |
| `services/api/` | FastAPI backend (M5–M7) |
| `scripts/` | Python CLI utilities and test data |
| `context/` | Milestone company scenarios (programme-assigned) |
| `specs/` | Implementation specifications |
| `public/index.html` | Local dev application hub |

## Agent infrastructure

See root `AGENTS.md` for session startup files, pre-commit workflow, and protected paths.

## Legacy note

The original static HTML site has been migrated to Next.js apps under `uis/`. The `assets/` folder remains for reference; Tailwind v3 build scripts are retained for historical compatibility only.
