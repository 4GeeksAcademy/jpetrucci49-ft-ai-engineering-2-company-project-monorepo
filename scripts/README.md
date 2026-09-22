# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## Python environment (uv)

Python scripts in this folder use **[uv](https://docs.astral.sh/uv/)** for dependency management. Configuration lives at the **repository root** — not in this folder.

| File | Purpose |
| --- | --- |
| `pyproject.toml` | Declares Python version and dependencies (e.g. `pandas`) |
| `uv.lock` | Locked dependency versions — commit this file |
| `.python-version` | Pin for local Python 3.12 |
| `.venv/` | Virtual environment created by `uv sync` (gitignored) |

### Setup

From the repository root:

```bash
uv sync
```

### Adding a dependency

From the repository root:

```bash
uv add <package-name>
```

## Scripts

| Script | Milestone | Purpose |
| --- | --- | --- |
| `analyze.py` | M5 | Offline aggregate analysis of `incidents.csv` |
| `seed_incidents.py` | M11 | Load validated CSV rows into the incident manager TinyDB |
| `nightly_export.py` | 7.1 | Export yesterday’s `telemetry_events` to CSV and trigger the clinic-supply pipeline |
| `nightly_loop.py` | 7.1 | Compose worker: sleep until 02:05 UTC, then run `nightly_export.py` |
| `forecast_sales.py` | 7.2 | Train XGBoost on consolidated `revenue_usd`; write test metrics and plot |
| `evaluate_sales_forecast.py` | 7.3 | 5-fold temporal CV + learning curve on 2016–2023; write diagnosis report |

---

### `analyze.py`

HealthCore patient incident CSV analysis CLI. Shares business rules with `services/api/app/incidents/analysis.py` and the M5 upload API.

**Requirements:** Python 3.12+ with **pandas**. Use either environment below.

#### Run from repo root (root `uv` env)

```bash
uv sync
uv run python scripts/analyze.py scripts/incidents.csv
```

#### Run with the API virtualenv (imports shared `app.incidents` modules)

When using `uv run --directory services/api`, paths are relative to `services/api/` — use **`../../scripts/`**:

```bash
# from repo root
uv run --directory services/api python ../../scripts/analyze.py ../../scripts/incidents.csv
```

```bash
# from services/api/
uv run python ../../scripts/analyze.py ../../scripts/incidents.csv
```

Optional: pass a different CSV path as the only argument.

**Expected for `scripts/incidents.csv`:** 100 total records, 94 valid, 6 invalid, average satisfaction 3.58.

#### Exit codes and errors

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Script ran but failed (wrong args, missing file, parse/analysis/write error) — message on **stderr** |
| `2` | Python could not start the script (wrong file path — e.g. `scripts/analyze.py` without `../../` when cwd is `services/api/`) |

Smoke tests:

```bash
# Wrong args → exit 1
uv run python scripts/analyze.py
echo $?   # 1

# Missing file → exit 1
uv run python scripts/analyze.py /nonexistent.csv
echo $?   # 1

# Happy path → exit 0 (prompts to export CSV)
uv run python scripts/analyze.py scripts/incidents.csv
echo $?   # 0
```

When using `--directory services/api`, prefix script and CSV paths with `../../scripts/` (see above).

---

### `seed_incidents.py`

Idempotent seeder for the **incident manager** (M11). Reads `scripts/incidents.csv`, validates each row with the same rules as M5 analysis (`services/api/app/incidents/csv_validation.py`), transforms valid rows into incident records, and inserts them into `services/api/incidents.json`.

**Requirements:** the **API virtualenv** (`services/api`) — the script imports FastAPI app modules and writes via TinyDB.

**Does not** store raw CSV, `patient_id`, or CSV enum values. Invalid or unmapped rows are counted as rejected, not inserted.

```bash
# from services/api/ (recommended)
uv run python ../../scripts/seed_incidents.py

# from repo root
uv run --directory services/api python ../../scripts/seed_incidents.py

# optional custom CSV path
uv run --directory services/api python ../../scripts/seed_incidents.py /path/to/incidents.csv
```

| Run | Expected output |
| --- | --- |
| First run | `inserted: 94`, `rejected: 6` |
| Later runs | `inserted: 0`, `skipped (duplicate): 94`, `rejected: 6` |

On failure (missing CSV, parse error, DB error), the script prints a short message to **stderr** and exits with code **`1`** (not `0`).

**Reset database:** from `services/api/`, delete `incidents.json` and run the seeder again. Override the TinyDB path with `INCIDENTS_DB_PATH` in `services/api/.env`.

After seeding, `GET /api/incidents/summary` should report **94** incidents — status `open` 28, `resolved` 52, `discarded` 14; categories `patient_experience` 61, `billing_error` 20, `other` 13. See `context/11_CONTEXT.md` and [`services/api/README.md`](../services/api/README.md#incident-manager-m11) for API endpoints and UI routes.

Spec: `specs/11_SPECS.md` §9.

---

### `nightly_export.py`

Independent nightly worker (not FastAPI). Exports UTC yesterday’s `telemetry_events` to `data/raw/telemetry_YYYY-MM-DD.csv` if that file is missing, then runs the Milestone 6 pipeline as a **subprocess**. Status and the `processing` lock live in `reporting.job_runs` via `services/jobs/job_runner.py`.

```bash
# from repo root
uv run python scripts/nightly_export.py
TARGET_DATE=2026-09-07 uv run python scripts/nightly_export.py
```

| Env | Meaning |
| --- | --- |
| `TARGET_DATE=YYYY-MM-DD` | Override “yesterday UTC” for tests |

A second run for a **completed** `target_date` exits 0 and skips export + pipeline. A second process while a row is `processing` exits 0 without work. Failures write `failed` (never leave `processing`).

**Trigger:** host crontab `deploy/nightly.crontab` (`5 2 * * *` UTC) or Compose service `nightly` (`scripts/nightly_loop.py`). Do not schedule this inside Uvicorn.

Spec: `specs/07.1_CRON_SPECS.md`.

---

### `forecast_sales.py`

Trains one XGBoost model on HealthCore **consolidated** monthly `revenue_usd` (`data/raw/healthcore_sales.csv`). First 8 years train, last 2 years test. Causal lags/rolls only. Writes metrics and the 2024–2025 plot under `data/eval/`.

```bash
# from repo root
uv sync
uv run python scripts/forecast_sales.py
```

| Exit | Meaning |
| --- | --- |
| `0` | Metrics and plot written |
| `1` | Load, feature, fit, or I/O failure (message on stderr) |

Report: [`data/pipelines/sales_forecast/README.md`](../data/pipelines/sales_forecast/README.md). Spec: `specs/07.2_TIMESERIES_SPECS.md`.

---

### `evaluate_sales_forecast.py`

5-fold temporal CV and a learning curve on **2016–2023** only (the 2024–2025 holdout is not used). Writes `data/eval/sales_forecast_cv_metrics.json`, `data/eval/sales_forecast_learning_curve.png`, and `data/eval/evaluation_report.md`.

```bash
# from repo root
uv sync
uv run python scripts/evaluate_sales_forecast.py
```

| Exit | Meaning |
| --- | --- |
| `0` | CV metrics, curve, and report written |
| `1` | Load, CV, or I/O failure (message on stderr) |

Spec: `specs/07.3_EVALUATION_SPECS.md`.

---

### `incidents.csv`

Sample patient-incident export used across M5 and M11:

| Consumer | How it is used |
| --- | --- |
| `analyze.py` | Offline CLI report |
| M5 API | `POST /api/incidents/analyze` (backoffice CSV upload) |
| `seed_incidents.py` | Historical data for the incident manager |

100 rows: **94 valid**, **6 invalid** (validation failures — same rules as M5).

> _Spanish version: [README.es.md](./README.es.md)._
