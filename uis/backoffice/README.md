# HealthCore Operations Backoffice

Internal dashboard: M2 operational utilities, M5 incident CSV analysis, M6 supplier directory, M11 centralized incident manager, M12 error handling.

## Stack

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · `@healthcore/utils` from `../../src/utils`

## Setup

From the repo root (recommended):

```bash
npm install
cd services/api && uv sync && cp .env.example .env && uv run seed && cd ../..
npm run dev
```

Set `JWT_SECRET` in `services/api/.env`. For password reset (M9), also set `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and `PASSWORD_RESET_URL` — see [`services/api/README.md`](../../services/api/README.md#password-recovery-and-change-m9). Supplier seed is idempotent (`0 inserted` with `15 total` means already loaded). Incident manager seed: [`scripts/README.md`](../../scripts/README.md#seed_incidentspy).

This app only:

```bash
npm install
cp .env.example .env   # cross-app nav URLs + FastAPI BFF proxy targets
npm run dev -- -p 3001
```

Ensure the API is running (`npm run dev:api` or full `npm run dev`).

Telemetry capture (M6.5) posts batches to the FastAPI stub. Copy `NEXT_PUBLIC_TELEMETRY_ENDPOINT` into `.env.local` (see `.env.example`) and restart `next dev`. Events go through `track()` only — never call the stub from a component. DevTools → Network: `POST http://localhost:8000/telemetry/events` should return `{ "received": N }`.

## Routes

| Route | Milestone | Purpose |
| --- | --- | --- |
| `/login`, `/register` | M8 | Sign in and registration |
| `/forgot-password`, `/reset-password` | M9 | Password recovery (public) |
| `/account/profile`, `/account/change-password` | M8/M9 | Profile and password change (authenticated) |
| `/` | M2 | Operations dashboard (billing, clinical, CME) |
| `/utilities` | M2 | Utility function manual runner |
| `/incidents` | M5 | Patient incident CSV upload and aggregate analysis |
| `/incidents/register` | M11 | Register a new incident (PHI warning on description) |
| `/incidents/manage` | M11 | List, filter, and update incident status |
| `/incidents/summary` | M11 | Leadership metrics by status, category, origin, branch |
| `/suppliers` | M6 | Supplier directory — browse, filter, register, rate/status |
| `/inventory/products` | M5.5 | Medical supply catalogue with current stock |
| `/inventory/orders/inbound` | M5.5 | Log a vendor delivery |
| `/inventory/orders/outbound` | M5.5 | Log a clinical consumption |
| `/inventory/orders` | M5.5 | Read-only supply movements |
| `/reporting` | M6.5 | Monthly Clinic Supply Performance Report (Dr. Okonkwo / Claire) |
| `/telemetry` | M6.5 | Engineering telemetry health (events, errors, latency, login failures) |

## Testing password recovery (M9)

1. Ensure Resend env vars are set in `services/api/.env` and `PASSWORD_RESET_URL=http://localhost:3001/reset-password`.
2. Register at http://localhost:3001/register (or use an existing account).
3. Go to `/login` → **Forgot your password?** → submit your email → confirmation message; form disables.
4. Open the reset link from email → set a new password → land on `/login` with success message.
5. Sign in with the new password.
6. Go to `/account/profile` → **Change password** → update password while logged in.

API-level curl tests: [`services/api/README.md`](../../services/api/README.md#testing). Full UI + API checklist: root [`README.md`](../../README.md#testing-password-recovery-and-change-m9).

## BFF proxy pattern

The browser calls same-origin `/api/*` routes. Next.js proxies server-side to FastAPI at `http://127.0.0.1:8000` (no direct browser access to port 8000) and forwards the bearer token from `localStorage` via `authFetch`.

| Env var | Default | Used by |
| --- | --- | --- |
| `INCIDENTS_API_URL` | `http://127.0.0.1:8000` | `/api/incidents/*` (M5 analyze/export and M11 manager) |
| `SUPPLIERS_API_URL` | `http://127.0.0.1:8000` | `/api/suppliers/*` |
| `AUTH_API_URL` | `http://127.0.0.1:8000` | `/api/auth/*`, `/api/users`, `/api/profiles/*` |
| `INVENTORY_API_URL` | `http://127.0.0.1:8000` | `/api/inventory/*`, `/api/reporting/*`, `/api/telemetry/*` |

### Error handling (M12)

| File | Role |
| --- | --- |
| `lib/api/bff-proxy.ts` | `runBffHandler()` — JSON parse errors → **400**, upstream/network failures → **502**, sanitizes validation `detail` |
| `components/ui/ErrorState.tsx` | Reusable error panel with optional retry |
| `app/error.tsx`, `app/global-error.tsx` | Safe user-facing copy (no raw `error.message`) |

List, summary, supplier, and profile flows show **loading / error / success** states with retry where appropriate. Shared helpers: `packages/shared/api/errors.ts`, `packages/shared/auth/errors.ts` (`humanizeValidationMessage`).

Spec / audit: `specs/12_SPECS.md` · Progress: `memory-bank/progress.md` § M12.

## Feature reference

### Incidents — CSV analysis (M5)

| File | Role |
| --- | --- |
| `lib/api/incidents.ts` | Client fetch helpers (analyze, export) |
| `lib/api/incidents-server.ts` | Server proxy utilities |
| `app/api/incidents/analyze/route.ts` | Upload BFF |
| `app/api/incidents/results/export/route.ts` | Export BFF |
| `components/incidents/IncidentAnalysisPage.tsx` | Upload UI and results |

Test CSV: `scripts/incidents.csv`.

### Incidents — manager (M11)

| File | Role |
| --- | --- |
| `lib/api/incidents-manager.ts` | Client fetch helpers (CRUD, summary, status) |
| `app/api/incidents/route.ts` | List + create BFF |
| `app/api/incidents/summary/route.ts` | Summary BFF |
| `app/api/incidents/[id]/status/route.ts` | Status update BFF |
| `components/incidents/IncidentRegisterForm.tsx` | Registration form |
| `components/incidents/IncidentListPanel.tsx` | Filterable list + inline status |
| `components/incidents/IncidentSummaryPanel.tsx` | Aggregate metrics |
| `packages/shared/incidents/` | Shared enums, labels, lifecycle rules (`@healthcore/incidents`) |

Spec: `specs/11_SPECS.md`. After seeding (see [`scripts/README.md`](../../scripts/README.md#seed_incidentspy)), summary totals should show 94 incidents (`context/11_CONTEXT.md`).

- **Register:** all model fields; branch highlighted when origin is `branch`; prominent PHI warning on description
- **List:** filters for status, origin, branch; empty and error states; status dropdown respects lifecycle
- **Summary:** aggregate metrics by status, category, origin, and branch

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

### Medical supplies (M5.5)

| File | Role |
| --- | --- |
| `lib/api/inventory.ts` | Client helpers (list/get supplies, record delivery/consumption, list movements) |
| `lib/api/inventory-server.ts` | Server proxy to FastAPI `/inventory` |
| `app/api/inventory/**/route.ts` | BFF handlers |
| `components/inventory/` | Catalogue, vendor delivery, clinical consumption, movements |
| `types/inventory.ts` | API types, clinic/category labels, stock-level helper |

- **Catalogue** (`/inventory/products`) — name, SKU, category, unit, jurisdiction, current stock (0 red / 1–10 amber / >10 green)
- **Vendor delivery** (`/inventory/orders/inbound`) — supply selected by name; `?supply_id=` prefill; success keeps query supply
- **Clinical consumption** (`/inventory/orders/outbound`) — live current stock via `getSupply`; oversell warning; API insufficient-stock on the quantity field
- **Supply movements** (`/inventory/orders`) — read-only deliveries and consumptions
- Nav: **Supplies**, **Movements** in `BackofficeShell`

Spec: `specs/05.5_SPECS_FRONT.md`. Seed: `uv run --directory services/api python seed_inventory.py`.

### Clinic supply report (M6.5)

| File | Role |
| --- | --- |
| `lib/api/reporting.ts` | Client fetch for KPI pack + latest pipeline run |
| `app/api/reporting/**/route.ts` | BFF to FastAPI `/reporting/*` (`INVENTORY_API_URL`) |
| `components/reporting/ClinicSupplyReportPage.tsx` | Four CONTEXT KPI tables; clinic labels; no mixed-currency total |
| `lib/reporting/clinics.ts` | Slug → label map aligned with `PIPELINE_DESIGN.md` §4.2 |

Nav: **Clinic supply**. Seed the pack with `uv run python data/pipelines/pipeline.py --month-start 2026-08-01` against the same DB as the API, then reload `/reporting`. Empty `clinics` is expected until that run.

Spec: `specs/06.5_PREFECT_SPECS.md`.

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
