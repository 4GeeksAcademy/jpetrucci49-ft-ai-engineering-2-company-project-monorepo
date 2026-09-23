# HealthCore Monorepo — Tech Context

## Repository layout

```text
/
├── memory-bank/          # Agent session context (this folder)
├── AGENTS.md             # Root agent instructions
├── .agents/              # Development rules
├── skills/               # Reusable agent skills
├── context/              # Milestone company scenarios (read-only unless approved)
├── milestones/           # Programme requirements (read-only unless approved)
├── src/                  # M2 TypeScript utilities and types
├── scripts/              # Python helper scripts (M5 incident analysis)
├── services/api/         # FastAPI internal API (M5 incidents, M6 suppliers, M7 auth)
├── data/                 # Pipelines (orchestration), process (transforms), raw, eval
├── pyproject.toml        # Python dependencies (uv)
├── uv.lock               # Locked Python dependency versions
├── tests/utils/          # Vitest suites and shared fixtures
├── uis/                  # Next.js frontend applications
│   ├── website/          # Public corporate site (port 3000)
│   ├── backoffice/       # Internal operations dashboard (port 3001)
│   └── talent-pipeline-tracker/  # Recruitment UI (port 3002)
└── public/               # Dev application hub (port 4173)
```

## Stacks in use

| Area | Stack |
| --- | --- |
| Root / M2 | TypeScript, Vitest, `concurrently`, `src/utility-registry.ts` |
| `scripts/` (M5) | Python 3.12+, [uv](https://docs.astral.sh/uv/), pandas |
| `services/api/` (M5–M7, M5.5) | Python 3.12+, FastAPI, uvicorn, pandas, TinyDB (M6), SQLModel + psycopg (M5.5 inventory), PyJWT + libpass (M7) |
| All `uis/*` | Next.js 16, React 19, Tailwind CSS v4 |

## Architectural decisions

1. **One Next.js app per UI** under `uis/<name>/` — independent `package.json`, dev server, and deploy boundary.
2. **Business logic lives in `src/utils/`** — frontends import via path aliases; never copy utility source into `uis/`.
3. **Client-side fetching when URL state matters** — e.g. talent tracker filters use `useSearchParams` + client refetch so list and query string stay in sync.
4. **Human-readable labels in UI** — map raw API/domain values to labels (status/stage in M3; compliance status in CME reports).
5. **No external state libraries** in Next.js apps — React hooks only.
6. **M5 incident analysis** — business rules in `services/api/app/incidents/analysis.py`; backoffice proxies via `app/api/incidents/` route handlers; client uses same-origin `/api/incidents/*`.
7. **M6 supplier directory** — Pydantic models + TinyDB in `services/api/`; REST at `/suppliers`; backoffice proxies via `app/api/suppliers/`; seed with `uv run --directory services/api seed`.
8. **M7 authentication** — Users + profiles in TinyDB (`auth.json`); JWT bearer tokens (PyJWT HS256); libpass bcrypt; `JWT_SECRET` required via `services/api/.env`; supplier and incident routes require auth.
9. **M8 frontend auth** — `localStorage` token; `packages/shared/auth/` + `authFetch`; BFF forwards `Authorization`; internal apps guard routes except `/login` and `/register`; website stays public.
10. **M9 password recovery (API)** — Reset tokens in TinyDB; Resend transactional email; `PASSWORD_RESET_URL` + `RESEND_*` env vars; public forgot/reset routes; authenticated change-password.
11. **M5.5 inventory** — SQLModel + psycopg3 (`postgresql+psycopg://` in `SUPABASE_DATABASE_URL`) on Postgres/SQLite; TinyDB auth unchanged; `user_uuid` copied from JWT; `current_stock` aggregated, never stored. FastAPI under `/inventory`. Backoffice UI at `/inventory/products` and `/inventory/orders*`; BFF `app/api/inventory/*` via `INVENTORY_API_URL` (default `http://127.0.0.1:8000`); client never calls `:8000`.
12. **M13 Docker Compose** — `ui` (website + backoffice, `next dev`) and `api` (Uvicorn `--reload`) on network `healthcore`. Bind-mount source for hot reload; named volumes for `node_modules` and `.next` so host caches do not overlay the container. In Docker, BFF targets are `http://api:8000`; browser/`NEXT_PUBLIC_*`/CORS/`PASSWORD_RESET_URL` stay on `localhost`. Root `.env` feeds both services; native app `.env.example` files still use loopback.
13. **M6.5 telemetry** — Backoffice `lib/telemetry/` queues events and POSTs `{ events: [...] }` to `NEXT_PUBLIC_TELEMETRY_ENDPOINT`. FastAPI `POST /telemetry/events` is unauthenticated, validates each envelope independently, and bulk-inserts valid rows into `telemetry_events` (same SQLModel engine as inventory). Response `{ received, stored, rejected }`. `GET /telemetry/report` is authenticated: the route resolves the UTC window (default last 7 days), caches `build_report` for 60s, and does not compute metrics itself. Pipeline: SQL load → Pandas refine/convert/`groupby`. Backoffice `/telemetry` proxies via `/api/telemetry/report`. All UI capture goes through `track()`.
14. **Monthly clinic supply performance (design)** — Orchestration will live in `data/pipelines/`; transforms in `data/process/`; HTTP in `services/api/reporting/` importing those modules. Destination is `reporting.monthly_clinic_supply_performance`, not `telemetry_events`. See `data/pipelines/PIPELINE_DESIGN.md`. `GET /telemetry/report` stays engineering-only.
15. **Monthly clinic supply performance (Prefect 3)** — Flow `monthly_clinic_supply_performance` in `data/pipelines/monthly_clinic_supply_performance/`. CLI entry `data/pipelines/pipeline.py`. Transforms in `data/process/` (`clinic_dimension`, `inbound_cost`, `clinic_month_kpis`). Load upserts `(clinic_id, month_start)`. HTTP in `services/api/reporting/` (not `telemetry/`): `GET /reporting/monthly-clinic-supply-performance`, `GET /reporting/pipeline-runs/latest`, `POST /reporting/pipeline-runs`. `GET /telemetry/report` and `telemetry/analysis.py` stay engineering-only.
16. **Clinic supply subflows + board pack** — Main flow orchestrates named subflows (`extract_monthly_clinic_supply_events`, `transform_monthly_clinic_supply_kpis`, `load_monthly_clinic_supply_performance`, optional `snapshot_monthly_clinic_supply_eval`). Isolated KPI tests: `uv run python -m pytest tests/pipelines/test_pipeline.py` (root `pytest` `testpaths`). Backoffice `/reporting` proxies via `/api/reporting/*` (`INVENTORY_API_URL`); UI maps slugs to clinic labels and does not compute KPIs. Optional Prefect Cloud: gitignored `PREFECT_API_KEY` + `PREFECT_API_URL`; `PREFECT_HOME` is repo `.prefect/`. Tests keep the ephemeral server.
17. **Nightly export (7.1)** — `scripts/nightly_export.py` is a process separate from Uvicorn. It writes `data/raw/telemetry_YYYY-MM-DD.csv` (backup only) and subprocesses `data/pipelines/pipeline.py --month-start <first of month> --no-sample`. Orchestration status is `reporting.job_runs` via `services/jobs/job_runner.py` (not `pipeline_runs`). Lock = a `processing` row. `TARGET_DATE` overrides yesterday UTC. Schedule: crontab `5 2 * * *` UTC (`deploy/nightly.crontab`) or Compose `nightly` (`scripts/nightly_loop.py`). Tests: `uv run python -m pytest tests/jobs`.
18. **Sales forecast (7.2)** — `scripts/forecast_sales.py` loads `data/raw/healthcore_sales.csv` (`region == consolidated`, target `revenue_usd`). Causal features and the 8-year / 2-year split live in `data/process/sales_forecast.py`. Model is XGBoost (`random_state=42`). Artifacts: `data/eval/sales_forecast_metrics.json` and `data/eval/sales_forecast_test.png`. Tests: `tests/pipelines/test_sales_forecast.py`.
19. **Sales forecast evaluation (7.3)** — `scripts/evaluate_sales_forecast.py` runs prefix-safe `TimeSeriesSplit` (5 folds) and a learning curve on **2016–2023 only**. Logic in `data/process/sales_forecast_eval.py`. Artifacts: `data/eval/sales_forecast_cv_metrics.json`, `sales_forecast_learning_curve.png`, `evaluation_report.md`. Tests: `tests/pipelines/test_sales_forecast_cv.py`.

## Technical constraints

- TypeScript `strict` mode in all apps
- Do not commit `.env.local` or secrets; commit `.env.example` when env vars are required
- Do not modify `context/` or `milestones/` without explicit developer approval
- M2 function signatures and entity interfaces must remain compatible with `tests/utils/`

## Key commands

```bash
# All apps + dev hub
npm run dev

# Root (M2)
npm run typecheck
npm test
npm run build        # all Next.js apps
npm run lint:apps

# Python scripts (M5) — from repo root
uv sync
uv run python scripts/analyze.py scripts/incidents.csv

# Same script via API venv (paths relative to services/api/)
uv run --directory services/api python ../../scripts/analyze.py ../../scripts/incidents.csv

# Monthly clinic supply performance (Prefect 3) — previous UTC month
uv sync --group dev
uv run python data/pipelines/pipeline.py
uv run python data/pipelines/pipeline.py --month-start 2026-08-01
uv run python -m pytest tests/pipelines/test_pipeline.py
uv run python -m pytest tests/jobs
uv run python scripts/nightly_export.py
# TARGET_DATE=2026-09-07 uv run python scripts/nightly_export.py
uv run python scripts/forecast_sales.py
uv run python scripts/evaluate_sales_forecast.py
uv run python -m pytest tests/pipelines/test_sales_forecast.py tests/pipelines/test_sales_forecast_cv.py
# Optional Prefect Cloud (after PREFECT_API_KEY in services/api/.env):
# PREFECT_HOME="$(pwd)/.prefect" uv run prefect cloud login --key "$PREFECT_API_KEY"
# uv run prefect config view

# HealthCore API (M5–M7)
cd services/api && uv sync && cp .env.example .env && uv run seed && uv run --env-file .env uvicorn app.main:app --reload --port 8000
npm run dev:api
uv run --directory services/api seed   # from repo root
uv run --directory services/api python seed_inventory.py   # inventory (needs a TinyDB user)

# Docker (website :3000, backoffice :3001, API :8000, nightly worker)
cp .env.example .env
docker compose up --build
docker compose exec api python seed.py
docker compose exec api python seed_inventory.py
```

## Path aliases (backoffice)

| Alias | Target |
| --- | --- |
| `@/*` | `uis/backoffice/*` |
| `@healthcore/utils` | `src/utils` |
| `@healthcore/fixtures` | `tests/utils/fixtures` |
| `@healthcore/utility-registry` | `src/utility-registry` |
