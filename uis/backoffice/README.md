# HealthCore Operations

Internal HealthCore Digital dashboard surfacing Milestone 2 operational reporting utilities and Milestone 5 patient incident analysis.

## Stack

- Next.js 16 (App Router)
- React 19 + TypeScript
- Tailwind CSS v4
- Imports `@healthcore/utils` from `../../src/utils` (not copied)

## Setup

```bash
npm install
cp .env.example .env
npm run dev -- -p 3001
```

From the repo root, `npm run dev` starts the backoffice on port **3001** alongside the API and other apps.

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Operations dashboard (billing, clinical, CME) |
| `/utilities` | M2 utility tester |
| `/incidents` | Patient incident CSV upload and analysis (M5) |

## Incident analysis (M5)

The browser calls same-origin `/api/incidents/*` routes. Next.js proxies those requests server-side to FastAPI (`INCIDENTS_API_URL`, default `http://127.0.0.1:8000`). This avoids CORS and remote-dev port-forwarding issues.

| File | Role |
| --- | --- |
| `lib/api/incidents.ts` | Client fetch helpers |
| `lib/api/incidents-server.ts` | Server-only proxy utilities |
| `app/api/incidents/*/route.ts` | BFF route handlers |
| `components/incidents/` | Upload UI and results panels |
| `types/incidents.ts` | API response types |

Test CSV: `data/raw/incidents.csv` at the repo root.

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
