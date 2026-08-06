# SPECS — Milestone 5 (Phase 2): Incident Analysis Platform Integration

Implementation specification for integrating the Phase 1 incident CSV analysis logic into the HealthCore platform — a FastAPI backend and a backoffice UI for Priya Nair's Patient Experience team. Build exactly what is described below.

This document covers **Phase 2 only**. Phase 1 (`scripts/analyze.py`) must be complete and verified before starting. See `05_SPECS_SCRIPT.md` for validation rules, expected metrics, and PHI constraints.

---

## 1. Objective

Once the CLI script logic is validated, **extract that same logic into reusable services** and integrate it into the monorepo:

1. **Backend** — `services/api/` exposes REST endpoints to upload a CSV, run analysis, and export the last result.
2. **Frontend** — `uis/backoffice/` adds an incident analysis page where staff upload a file, review the summary, and download results.

The API and UI must produce **the same numeric results** as `scripts/analyze.py` when run against `scripts/incidents.csv`. No patient identifiers or row-level PHI may appear in API responses, logs, or exports.

---

## 2. Company Context (Required Reading)

| File | Use |
| --- | --- |
| `context/05_CONTEXT.md` | CSV schema, validation rules, stakeholder notes, compliance requirements |
| `05_SPECS_SCRIPT.md` | Phase 1 behaviour, expected metrics (§6), export format |
| `scripts/analyze.py` | Reference implementation to extract — do not duplicate business rules in TypeScript |
| `scripts/incidents.csv` | Verification dataset (100 data rows) |
| `docs/ARCHITECTURE_PROPOSAL.md` | FastAPI layered structure guidance (adapt paths to `services/api/`) |

**Compliance (non-negotiable):** HIPAA / UK GDPR — `patient_id` and free-text `description` must never appear in JSON responses, error messages, server logs, or CSV exports. Report invalid-record **counts by rule type** only.

---

## 3. Shared Logic Extraction (Prerequisite)

Before building HTTP endpoints, refactor Phase 1 so **one Python module** owns all analysis logic. Both the CLI script and the API must import from it — no copy-paste.

### 3.1 Target layout

```text
services/api/
├── README.md
├── pyproject.toml              # FastAPI service deps (uv-managed)
├── app/
│   ├── main.py                 # FastAPI app, CORS, router mount
│   ├── core/
│   │   └── config.py           # Settings (port, CORS origins)
│   ├── incidents/
│   │   ├── analysis.py         # ← extracted: validate_record, analyze, export rows
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── router.py           # POST analyze, GET export
│   │   └── store.py            # In-memory last-result store
│   └── ...
scripts/
└── analyze.py                  # Thin CLI: load file → analyze → print → optional export
```

### 3.2 Functions to extract from `scripts/analyze.py`

Move into `services/api/app/incidents/analysis.py` (names may vary, behaviour must not):

| Function / constant | Purpose |
| --- | --- |
| `CLINIC_COUNTRIES`, `CATEGORIES`, `STATUSES`, `COUNTRIES`, `INVALID_RULE_LABELS`, `SCORE_LABELS` | Reference data |
| `validate_record(row)` | Returns list of rule keys violated |
| `load_incidents_from_bytes(content: bytes) -> DataFrame` | Parse UTF-8 CSV from upload (replaces path-based loader for API) |
| `load_incidents_from_path(path)` | Keep for CLI |
| `analyze(df) -> dict` | Same metrics dict as Phase 1 |
| `metrics_to_csv_rows(metrics) -> list[dict]` | Rows for CSV export (same as Phase 1 `export_csv`) |

### 3.3 CLI after refactor

`scripts/analyze.py` must:

- Import `analyze`, `load_incidents_from_path`, and CSV row builder from `services/api/app/incidents/analysis.py` (configure `PYTHONPATH` or use a uv workspace/package layout so imports resolve).
- Continue to pass all Phase 1 acceptance criteria in `05_SPECS_SCRIPT.md`.

### 3.4 Python environment

Use **uv** for `services/api/` (consistent with root `pyproject.toml` / Phase 1):

- Declare FastAPI, uvicorn, python-multipart, and pandas in `services/api/pyproject.toml`.
- Commit `services/api/uv.lock` (or use a uv workspace at repo root — document the chosen approach in `services/api/README.md`).
- Do **not** add `requirements.txt`.

---

## 4. Backend — `services/api/`

### 4.1 Stack

| Item | Value |
| --- | --- |
| Framework | FastAPI |
| Server | uvicorn (dev: `uv run uvicorn app.main:app --reload --port 8000`) |
| Python | 3.12+ |
| Package manager | uv |
| Default port | `8000` |
| API prefix | `/api` |

### 4.2 CORS

Enable CORS for the backoffice origin so browser `fetch` from `uis/backoffice` works in local dev:

| Origin | Port |
| --- | --- |
| `http://localhost:3001` | Backoffice dev server |

Read allowed origins from env (e.g. `CORS_ORIGINS`) with sensible defaults. Document in `services/api/README.md` and `.env.example`.

### 4.3 In-memory result store

`GET /api/incidents/results/export` returns the **last successful analysis** from the current API process.

- Implement a simple module-level store (e.g. `store.py`) holding the latest metrics dict and metadata (`analyzed_at`, `source_filename`).
- Overwrite on each successful `POST /api/incidents/analyze`.
- Return **404** if no analysis has been run yet.
- Document in README that this is intentional for the capstone; production would use persistent storage.

**Do not persist raw CSV content or row-level data** — only aggregate metrics needed for JSON response and CSV export.

---

## 5. API Endpoints

### 5.1 `POST /api/incidents/analyze`

Accept a CSV file and return the analysis summary as JSON.

| Item | Specification |
| --- | --- |
| Content-Type | `multipart/form-data` |
| Field name | `file` (required) |
| Success status | `200 OK` |
| Response body | JSON matching `AnalysisResult` schema (§5.3) |
| Side effect | Store result in memory for export endpoint |

**Validation flow:**

1. Reject missing file → `400` with `{ "detail": "No file uploaded." }`
2. Reject empty file (0 bytes or header-only) → `400` with descriptive message
3. Reject non-CSV extension or unreadable content → `400`
4. Reject CSV missing required columns (see `05_SPECS_SCRIPT.md` §3.3) → `400` with message listing expected columns — **do not include row data in the error**
5. Run the same `analyze()` logic as Phase 1 on successfully parsed data
6. Return JSON summary; save aggregates to store

**Success response must include:**

- Totals (`total`, `valid_count`, `invalid_count`)
- Invalid breakdown (each rule key + human-readable label + count)
- Category breakdown (count + percentage per category, valid records only)
- Status breakdown (count + percentage, valid records only)
- Country breakdown (count + percentage, valid records only) — recommended, include in JSON
- Satisfaction index (`closed_total`, `scored_total`, `average_score`, `score_counts` with labels)

### 5.2 `GET /api/incidents/results/export`

Return the last analysis as a downloadable CSV.

| Item | Specification |
| --- | --- |
| Success status | `200 OK` |
| Content-Type | `text/csv` |
| Content-Disposition | `attachment; filename="results.csv"` |
| Body | Same row format as Phase 1 (`metric`, `value`, `percentage`) |

| Condition | Status | Response |
| --- | --- | --- |
| No prior analysis in this process | `404` | `{ "detail": "No analysis results available. Upload a CSV first." }` |
| Results available | `200` | CSV file download |

### 5.3 JSON response schema (`AnalysisResult`)

Use Pydantic models in `schemas.py`. Illustrative shape:

```json
{
  "source_filename": "incidents.csv",
  "analyzed_at": "2026-08-03T18:30:00Z",
  "totals": {
    "total": 100,
    "valid_count": 94,
    "invalid_count": 6
  },
  "invalid_breakdown": [
    { "rule": "invalid_clinic_id", "label": "Invalid or missing clinic_id", "count": 1 },
    { "rule": "country_clinic_mismatch", "label": "Country/clinic mismatch", "count": 1 }
  ],
  "categories": [
    { "code": "APPOINTMENT", "count": 30, "percentage": 31.9 }
  ],
  "statuses": [
    { "code": "OPEN", "count": 28, "percentage": 29.8 }
  ],
  "countries": [
    { "code": "US", "count": 61, "percentage": 64.9 }
  ],
  "satisfaction": {
    "closed_total": 52,
    "scored_total": 52,
    "average_score": 3.58,
    "scores": [
      { "score": 1, "label": "Very dissatisfied", "count": 3 }
    ]
  }
}
```

Percentages: one decimal place. Average score: two decimal places. Numeric values must match Phase 1 §6 when tested with `scripts/incidents.csv`.

### 5.4 Error response format

Use FastAPI `HTTPException` with a string `detail` (or structured detail for validation errors). Examples:

| Scenario | HTTP | Example `detail` |
| --- | --- | --- |
| No file in multipart request | 400 | `"No file uploaded."` |
| Empty CSV | 400 | `"The uploaded file is empty."` |
| Missing required columns | 400 | `"Invalid CSV format: missing required columns: patient_id, status"` |
| Unparseable CSV | 400 | `"Unable to parse CSV file. Ensure UTF-8 encoding and comma separator."` |
| Export with no prior analysis | 404 | `"No analysis results available. Upload a CSV first."` |

Never include `patient_id` values or raw incident rows in error payloads.

### 5.5 OpenAPI

FastAPI auto-generates docs at `/docs`. Document the `file` upload field clearly in the router docstring/summary.

---

## 6. Frontend — `uis/backoffice/`

### 6.1 Stack & constraints

| Item | Value |
| --- | --- |
| App path | `uis/backoffice/` |
| Framework | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4 |
| State | React hooks only — no external state libraries |
| API base URL | `NEXT_PUBLIC_API_URL` (e.g. `http://localhost:8000`) |

Add to `uis/backoffice/.env.example`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 6.2 Route & navigation

| Route | Purpose |
| --- | --- |
| `/incidents` | Incident CSV upload and analysis results |

Add **Incidents** (or **Incident Analysis**) to `BackofficeShell` navigation alongside Dashboard and Utilities.

Frame the page for **Patient Experience** team — e.g. heading: "Patient Incident Analysis".

### 6.3 Page behaviour

The `/incidents` page must include:

#### File upload

- Drag-and-drop zone **and** file picker (`.csv` accepted).
- On file select, `POST` to `{NEXT_PUBLIC_API_URL}/api/incidents/analyze` as `multipart/form-data` with field name `file`.
- Show **loading state** while the request is in flight.
- Show **error state** with the API `detail` message on failure (400, network error, etc.) — never display raw CSV row content.

#### Results summary (on success)

Display all sections returned by the API:

| Section | Content |
| --- | --- |
| General metrics | Total records, valid count, invalid count |
| Invalid records | Alert or panel when `invalid_count > 0` — list each rule type with count (e.g. "Missing patient_id: 1") |
| Category breakdown | All five categories with count and percentage |
| Status breakdown | OPEN / CLOSED / DISCARDED with count and percentage |
| Satisfaction index | Scored cases, average score, distribution by score 1–5 |

Country breakdown: display if present in API response (recommended).

Use human-readable labels from the API — not raw rule keys alone.

#### Download CSV

- Button: **Download results CSV** (or equivalent).
- Calls `GET {NEXT_PUBLIC_API_URL}/api/incidents/results/export`.
- Triggers browser file download (`results.csv`).
- Disabled or hidden until a successful analysis exists in the current session; if clicked before analysis, show helpful message.
- Handle 404 from export endpoint gracefully.

### 6.4 Suggested component structure

```text
uis/backoffice/
├── app/incidents/page.tsx
├── components/incidents/
│   ├── IncidentAnalysisPage.tsx   # Page shell / state orchestration
│   ├── IncidentFileUpload.tsx     # Drag-drop + file input
│   ├── IncidentResultsSummary.tsx # Metrics panels
│   └── InvalidRecordsAlert.tsx    # Invalid breakdown emphasis
├── lib/api/incidents.ts           # analyzeIncidents(), exportResults()
└── types/incidents.ts             # TypeScript types mirroring AnalysisResult
```

Follow existing backoffice patterns (`BackofficeShell`, Tailwind slate/teal internal chrome).

### 6.5 UX requirements

- Mobile-responsive layout (stack panels on narrow viewports).
- Accessible file input (keyboard operable, visible focus states).
- Empty state before first upload — brief instructions referencing CSV format from Patient Experience workflow.
- Do not fail silently — every async operation shows loading, success, or error.

---

## 7. Local Development

### 7.1 Running services

Document in `services/api/README.md`:

```bash
# Terminal 1 — API
cd services/api
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — Backoffice
cd uis/backoffice
npm install
npm run dev   # port 3001
```

add root `npm run dev:api` script to run API alongside existing `npm run dev` apps.

### 7.2 Manual test plan

1. Start API and backoffice.
2. Open `http://localhost:3001/incidents`.
3. Upload `scripts/incidents.csv`.
4. Verify on-screen values match `05_SPECS_SCRIPT.md` §6 (100 total, 94 valid, 6 invalid, avg 3.58, etc.).
5. Click download — confirm `results.csv` matches Phase 1 export format.
6. Restart API — confirm export returns 404 until a new file is uploaded.
7. Upload empty file — confirm 400 and user-visible error message.
8. Confirm no `patient_id` appears in browser Network tab response bodies.

### 7.3 CLI regression

After refactor, re-run:

```bash
uv run python scripts/analyze.py scripts/incidents.csv
```

All Phase 1 numeric output must still match §6.

---

## 8. Code Structure (Target)

```text
/
├── pyproject.toml                    # Root Python / CLI (Phase 1)
├── scripts/analyze.py                # CLI wrapper → shared analysis module
├── services/
│   └── api/
│       ├── README.md
│       ├── pyproject.toml
│       ├── uv.lock
│       ├── .env.example
│       └── app/
│           ├── main.py
│           └── incidents/
│               ├── analysis.py       # Shared business logic
│               ├── schemas.py
│               ├── router.py
│               └── store.py
└── uis/backoffice/
    ├── .env.example                  # NEXT_PUBLIC_API_URL
    ├── app/incidents/page.tsx
    ├── components/incidents/...
    ├── lib/api/incidents.ts
    └── types/incidents.ts
```

---

## 9. Acceptance Criteria — Phase 2

### Shared logic refactor

- [ ] Analysis logic lives in importable module under `services/api/` — not duplicated in the API router or backoffice TypeScript.
- [ ] `scripts/analyze.py` imports shared module and still passes Phase 1 verification.

### Backend (`services/api/`)

- [ ] Create `POST /api/incidents/analyze` accepting CSV as `multipart/form-data` (field: `file`).
- [ ] Endpoint runs the same validation and analysis as the script; returns summary JSON.
- [ ] Create `GET /api/incidents/results/export` returning last analysis as downloadable CSV.
- [ ] Errors (empty file, incorrect format, missing columns, no prior export) return appropriate HTTP status with descriptive `detail` — no PHI in messages.
- [ ] CORS configured for backoffice dev origin.
- [ ] Service documented in `services/api/README.md` with uv setup and run commands.

### Frontend (`uis/backoffice/`)

- [ ] Incident analysis page at `/incidents`, linked from application navigation.
- [ ] File upload (drag & drop and file selector) sends CSV to `POST /api/incidents/analyze`.
- [ ] Results summary on screen: general metrics, category breakdown, status breakdown, satisfaction index.
- [ ] Invalid records called out — count per rule type when present.
- [ ] Button to download results CSV via export endpoint.
- [ ] Loading and error states for upload and download.
- [ ] `NEXT_PUBLIC_API_URL` in `.env.example`.

### Compliance & accuracy

- [ ] No `patient_id` or row-level PHI in API JSON, CSV export, UI, or server logs.
- [ ] Uploading `scripts/incidents.csv` produces numeric results matching `05_SPECS_SCRIPT.md` §6.

### Quality

- [ ] `npm run lint` and `npm run build` pass in `uis/backoffice/`.
- [ ] Phase 1 CLI still produces correct output after refactor.

---

## 10. Out of Scope (Phase 2)

- Database persistence for analysis history
- Authentication / role-based access (internal tool — trust network boundary for capstone)
- Integrating incident metrics into the main operations dashboard (`/`) — optional follow-up
- Processing or storing the full 1,000-row production archive server-side long-term
- Replacing Phase 1 CLI workflow (script remains for batch/offline use)
- External AI services or third-party analytics on uploaded CSVs

---

## 11. References

- `context/05_CONTEXT.md` — company scenario, CSV schema, compliance
- `05_SPECS_SCRIPT.md` — Phase 1 spec, validation rules, expected values (§6)
- `scripts/analyze.py` — reference implementation to extract
- `docs/ARCHITECTURE_PROPOSAL.md` — FastAPI domain structure (adapt to `services/api/`)
- `uis/backoffice/components/layout/BackofficeShell.tsx` — navigation pattern
- `uis/talent-pipeline-tracker/lib/api/client.ts` — fetch/error handling reference
- `services/README.md` — services folder conventions
