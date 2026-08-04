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
├── services/api/         # FastAPI internal API (M5 incident analysis)
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
| `services/api/` (M5) | Python 3.12+, FastAPI, uvicorn, pandas |
| All `uis/*` | Next.js 16, React 19, Tailwind CSS v4 |

## Architectural decisions

1. **One Next.js app per UI** under `uis/<name>/` — independent `package.json`, dev server, and deploy boundary.
2. **Business logic lives in `src/utils/`** — frontends import via path aliases; never copy utility source into `uis/`.
3. **Client-side fetching when URL state matters** — e.g. talent tracker filters use `useSearchParams` + client refetch so list and query string stay in sync.
4. **Human-readable labels in UI** — map raw API/domain values to labels (status/stage in M3; compliance status in CME reports).
5. **No external state libraries** in Next.js apps — React hooks only.
6. **M5 incident analysis** — business rules in `services/api/app/incidents/analysis.py`; backoffice proxies via `app/api/incidents/` route handlers; client uses same-origin `/api/incidents/*`.

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

# Python scripts (M5)
uv sync
uv run python scripts/analyze.py data/raw/incidents.csv

# HealthCore API (M5)
cd services/api && uv sync && uv run uvicorn app.main:app --reload --port 8000
npm run dev:api
```

## Path aliases (backoffice)

| Alias | Target |
| --- | --- |
| `@/*` | `uis/backoffice/*` |
| `@healthcore/utils` | `src/utils` |
| `@healthcore/fixtures` | `tests/utils/fixtures` |
| `@healthcore/utility-registry` | `src/utility-registry` |
