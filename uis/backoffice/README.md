# HealthCore Operations

Internal HealthCore Digital dashboard surfacing Milestone 2 operational reporting utilities, Milestone 5 patient incident analysis, and Milestone 6 supplier directory.

## Stack

- Next.js 16 (App Router)
- React 19 + TypeScript
- Tailwind CSS v4
- Imports `@healthcore/utils` from `../../src/utils` (not copied)

## Setup

From the repository root (recommended):

```bash
npm install
cd services/api && uv sync && uv run seed && cd ../..
npm run dev
```

The seed step loads 15 suppliers into TinyDB for `/suppliers`. It is idempotent — `0 inserted` with `15 total` means data is already present.

This app only, from `uis/backoffice/`:

```bash
npm install
cp .env.example .env.local   # optional — custom FastAPI proxy URLs
npm run dev -- -p 3001
```

Ensure the API is running (`npm run dev:api` from repo root, or include it via `npm run dev`).

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Operations dashboard (billing, clinical, CME) |
| `/utilities` | M2 utility tester |
| `/incidents` | Patient incident CSV upload and analysis (M5) |
| `/suppliers` | Supplier directory — browse, filter, register, update rate/status (M6) |

## Incident analysis (M5)

The browser calls same-origin `/api/incidents/*` routes. Next.js proxies those requests server-side to FastAPI (`INCIDENTS_API_URL`, default `http://127.0.0.1:8000`). This avoids CORS and remote-dev port-forwarding issues.

| File | Role |
| --- | --- |
| `lib/api/incidents.ts` | Client fetch helpers |
| `lib/api/incidents-server.ts` | Server-only proxy utilities |
| `app/api/incidents/*/route.ts` | BFF route handlers |
| `components/incidents/` | Upload UI and results panels |
| `types/incidents.ts` | API response types |

Test CSV: `scripts/incidents.csv`.

## Supplier directory (M6)

The browser calls same-origin `/api/suppliers/*` routes. Next.js proxies to FastAPI (`SUPPLIERS_API_URL`, default `http://127.0.0.1:8000`).

| File | Role |
| --- | --- |
| `lib/api/suppliers.ts` | Client fetch helpers |
| `lib/api/suppliers-server.ts` | Server-only proxy utilities |
| `app/api/suppliers/**/route.ts` | BFF route handlers (list, create, rate, status; DELETE proxied for API use only) |
| `components/suppliers/` | Directory page, table, filters, registration form |
| `types/suppliers.ts` | API types and category labels |

**Before testing:** run `uv run --directory services/api seed` (or `uv run seed` from `services/api/`). Spec: `specs/06_SPECS_FRONTEND.md`.

UI highlights:

- Filters by country and category (client refetch, no page reload)
- **Register new supplier** button reveals the registration form above the table
- Click-to-edit monthly rate with explicit Save; list sorted by name
- Suspend / activate per row (suppliers are retained for audit history — no delete action in the UI)

## Dashboard sections

| Section | Owner | M2 functions |
| --- | --- | --- |
| Revenue Cycle & Billing | Tom Callahan | `calculateDenialRate`, `denialRateByPayer`, `flagHighDenialPayers` |
| Clinical Operations | Dr. Marcus Reid | `noShowRateByLocation`, `flagHighNoShowLocations` |
| People & Workforce | Diane Foster | `generateCMEReport`, `getCliniciansAtRisk` |

Sample data loaded from `@healthcore/fixtures` (`tests/utils/fixtures.ts`).

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Development server |
| `npm run build` | Production build |
| `npm run start` | Run production server |
| `npm run lint` | ESLint |
