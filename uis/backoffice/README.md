# HealthCore Operations Backoffice

Internal dashboard: M2 operational utilities, M5 incident analysis, M6 supplier directory.

## Stack

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · `@healthcore/utils` from `../../src/utils`

## Setup

From the repo root (recommended):

```bash
npm install
cd services/api && uv sync && cp .env.example .env && uv run seed && cd ../..
npm run dev
```

Set `JWT_SECRET` in `services/api/.env`. Seed is idempotent — `0 inserted` with `15 total` means suppliers are already loaded.

This app only:

```bash
npm install
cp .env.example .env   # cross-app nav URLs + FastAPI BFF proxy targets
npm run dev -- -p 3001
```

Ensure the API is running (`npm run dev:api` or full `npm run dev`).

## Routes

| Route | Milestone | Purpose |
| --- | --- | --- |
| `/` | M2 | Operations dashboard (billing, clinical, CME) |
| `/utilities` | M2 | Utility function manual runner |
| `/incidents` | M5 | Patient incident CSV upload and analysis |
| `/suppliers` | M6 | Supplier directory — browse, filter, register, rate/status |

## BFF proxy pattern

The browser calls same-origin `/api/*` routes. Next.js proxies server-side to FastAPI at `http://127.0.0.1:8000` — no direct browser access to port 8000, avoiding CORS and Codespaces port-forwarding issues.

| Env var | Default | Used by |
| --- | --- | --- |
| `INCIDENTS_API_URL` | `http://127.0.0.1:8000` | `/api/incidents/*` |
| `SUPPLIERS_API_URL` | `http://127.0.0.1:8000` | `/api/suppliers/*` |

### M7 auth note

Supplier and incident API routes now require JWT auth. The BFF does **not** forward `Authorization` headers yet — those pages may return **401** until a follow-up milestone. Test auth directly via [`services/api/README.md`](../../services/api/README.md) and `/docs`.

## Feature reference

### Incidents (M5)

| File | Role |
| --- | --- |
| `lib/api/incidents.ts` | Client fetch helpers |
| `lib/api/incidents-server.ts` | Server proxy utilities |
| `app/api/incidents/*/route.ts` | BFF handlers |
| `components/incidents/` | Upload UI and results |

Test CSV: `scripts/incidents.csv`.

### Suppliers (M6)

| File | Role |
| --- | --- |
| `lib/api/suppliers.ts` | Client fetch helpers |
| `lib/api/suppliers-server.ts` | Server proxy utilities |
| `app/api/suppliers/**/route.ts` | BFF handlers |
| `components/suppliers/` | Directory, filters, registration |

- Filters sync to URL query strings (`?country=&category=`)
- **Register new supplier** reveals form above the table
- Click-to-edit monthly rate with explicit Save
- Suspend / activate only — no delete in UI (per `context/06_CONTEXT.md`)

Spec: `specs/06_SPECS_FRONTEND.md`.

## Dashboard sections (M2)

| Section | Owner | Functions |
| --- | --- | --- |
| Revenue Cycle & Billing | Tom Callahan | `calculateDenialRate`, `denialRateByPayer`, `flagHighDenialPayers` |
| Clinical Operations | Dr. Marcus Reid | `noShowRateByLocation`, `flagHighNoShowLocations` |
| People & Workforce | Diane Foster | `generateCMEReport`, `getCliniciansAtRisk` |

Sample data: `@healthcore/fixtures` (`tests/utils/fixtures.ts`).

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Development server (port 3001) |
| `npm run build` | Production build |
| `npm run start` | Run production server |
| `npm run lint` | ESLint |
