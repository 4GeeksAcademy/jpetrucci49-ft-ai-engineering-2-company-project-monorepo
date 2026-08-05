# SPECS — Milestone 5 (Phase 1): Incident Report Analysis Script

Implementation specification for the HealthCore patient incident CSV analysis utility. Build exactly what is described below.

This milestone is delivered in **two phases**. This document covers **Phase 1 only** — the command-line analysis script under `scripts/`. Phase 2 will be specified separately.

---

## 1. Objective

Build a Python script that reads HealthCore's exported incident spreadsheet, validates each record against business rules, prints a stakeholder-ready summary to the console, and optionally exports metrics to CSV.

---

## 2. Company Context (Required Reading)

Before implementing anything, read:

| File | Use |
| --- | --- |
| `context/05_CONTEXT.md` | CSV schema, validation rules, expected output, compliance requirements |
| `scripts/incidents.csv` | Test dataset (100 data rows + header) used for verification |

Stakeholder constraints from the context:

- **HIPAA / UK GDPR:** `patient_id` is protected health information. It must **never** appear in console output, logs, error messages, or CSV export — only aggregate rule-violation counts (e.g. "Missing patient_id: 1 record").
- **Accuracy:** Numeric values in required sections must match the expected values in §6 exactly when run against `scripts/incidents.csv`.
- **Optional extension:** A breakdown by country (`US` / `UK`) on valid records is recommended for stakeholders but **not required** for a passing submission.

---

## 3. Phase 1 — Analysis Script (`scripts/`)

### 3.1 Location & stack

| Item | Value |
| --- | --- |
| Script path | `scripts/analyze.py` |
| Language | Python 3.12+ |
| Package manager | **[uv](https://docs.astral.sh/uv/)** — dependencies declared in root `pyproject.toml`, lockfile `uv.lock` |
| Dependencies | **pandas** for CSV loading and aggregation (declared in `pyproject.toml`). The standard library `csv` module is acceptable if you avoid pandas, but pandas is the recommended approach for tabular analysis. |
| Virtual environment | `.venv/` at repository root (created by `uv sync`; gitignored) |
| Input file | Path passed as a **command-line argument** — not hard-coded |
| Default export path | `results.csv` in the **current working directory** when the user confirms export |

#### Environment setup

From the repository root:

```bash
uv sync
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available. Do **not** use `requirements.txt` — all Python dependencies are managed through `pyproject.toml` and `uv.lock`.

### 3.2 Command-line interface

The script must be runnable as:

```bash
uv run python scripts/analyze.py scripts/incidents.csv
```

Requirements:

- Accept exactly one positional argument: path to the CSV file.
- If the path is missing, does not exist, or is not readable, exit with a clear error message (no PHI in the message).
- Display the source filename in the report header (basename is sufficient, e.g. `incidents.csv`).

### 3.3 Loading the CSV

- Read UTF-8 encoded CSV with comma separator and header row (row 1).
- Expected columns (from `context/05_CONTEXT.md`):

| Field | Type | Required |
| --- | --- | --- |
| `incident_id` | string | ✅ |
| `date` | string (`YYYY-MM-DD`) | ✅ |
| `clinic_id` | string | ✅ |
| `country` | string (`US` or `UK`) | ✅ |
| `category` | string | ✅ |
| `description` | string | ✅ |
| `status` | string | ✅ |
| `patient_id` | string | ✅ |
| `satisfaction_score` | integer | ❌\* |

\*Required when `status = CLOSED`; see validation rules below.

- Treat empty strings and whitespace-only values as missing where applicable.
- Do not print raw row contents during validation failures.

### 3.4 Valid reference data

#### Valid clinic codes (12)

| Code | Country |
| --- | --- |
| `US-TX-01`, `US-TX-02`, `US-TX-03` | US |
| `US-FL-01`, `US-FL-02`, `US-FL-03` | US |
| `US-GA-01`, `US-GA-02`, `US-GA-03` | US |
| `UK-LON-01`, `UK-LON-02` | UK |
| `UK-MAN-01` | UK |

A record is invalid if `country` does not match the country implied by `clinic_id` (US clinics → `US`, UK clinics → `UK`).

#### Valid categories (5)

`APPOINTMENT`, `BILLING`, `CLINICAL_CARE`, `ACCESSIBILITY`, `ADMINISTRATIVE`

#### Valid status values (3)

`OPEN`, `CLOSED`, `DISCARDED` (case-sensitive as stored in the CSV)

#### Valid `patient_id` format

`PAT-XXXXXX` (regex: `^PAT-\d{6}$` or equivalent validation)

#### Valid `satisfaction_score`

Integer **1–5** inclusive when present.

### 3.5 Invalid record detection

Flag a record as **invalid** if **any** of the following rules apply. A record may trigger multiple rules internally, but the breakdown counts **one increment per rule type** across all invalid records (each rule counted independently per record that violates it).

| Rule key | Condition |
| --- | --- |
| Invalid or missing `clinic_id` | Empty or not one of the 12 valid clinic codes |
| Country/clinic mismatch | `country` does not match the clinic's country |
| Invalid or missing `category` | Empty or not one of the 5 valid categories |
| Empty description | Empty or fewer than 5 characters |
| Missing `patient_id` | Empty or does not match `PAT-XXXXXX` format |
| Closed case, no score | `status = CLOSED` and `satisfaction_score` is missing/empty |
| Out-of-range score | `satisfaction_score` present but not an integer 1–5 |

**Processing order:**

1. Evaluate all rules and collect invalid records.
2. **Valid records** = all rows that fail **none** of the rules above.
3. All category, status, country, and satisfaction metrics are computed on **valid records only**, except totals that explicitly count valid vs invalid.

Report the invalid breakdown in console output with human-readable labels matching `context/05_CONTEXT.md` (see §3.7). Never include `patient_id`, `description` text, or other PHI in violation messages.

### 3.6 Metrics to calculate

#### Totals

| Metric | Scope |
| --- | --- |
| Total records in file | All data rows (exclude header) |
| Valid records | Rows passing all validation rules |
| Invalid / incomplete records | Rows failing one or more rules |

#### Breakdown by category (valid records)

Count and percentage of valid records for each of the five categories. Percentage = `(count / valid_total) * 100`, rounded to **one decimal place** for display (e.g. `31.9%`).

#### Breakdown by status (valid records)

Count and percentage for `OPEN`, `CLOSED`, and `DISCARDED` on valid records only.

#### Breakdown by country (valid records) — recommended, not required

Count and percentage for `US` and `UK` on valid records only.

#### Satisfaction index (closed cases, valid records)

Consider only valid records where `status = CLOSED`:

| Metric | Rule |
| --- | --- |
| Scored cases | Count of closed valid records that have a recorded score (after validation, all closed valid records should have a score) |
| Average score | Mean of `satisfaction_score` for those closed valid records, rounded to **two decimal places** (e.g. `3.58`) |
| Score distribution | Count per score 1–5 |

Use labels from the context for score descriptions where shown:

| Score | Label |
| --- | --- |
| 1 | Very dissatisfied |
| 2 | Dissatisfied |
| 3 | Neutral |
| 4 | Satisfied |
| 5 | Very satisfied |

### 3.7 Console output format

Print a readable summary to stdout. Use separators, clear section headings, tree-style prefixes (`├─`, `└─`), and aligned labels. Minor formatting differences (spacing, box-drawing characters) are acceptable; **numeric values in required sections must match exactly**.

Required structure (adapt spacing as needed):

```
============================================================
  HEALTHCORE — PATIENT INCIDENT REPORT ANALYSIS
  Source file: <filename>
============================================================

TOTAL RECORDS IN FILE .......... <N>
  ├─ Valid records ................ <valid>
  └─ Invalid / incomplete .......... <invalid>

INVALID RECORDS BREAKDOWN
  ├─ Invalid or missing clinic_id .. <count>
  ├─ Country/clinic mismatch ....... <count>
  ├─ Invalid or missing category ... <count>
  ├─ Empty description ............. <count>
  ├─ Missing patient_id ............ <count>
  └─ Closed case, no score ......... <count>

BREAKDOWN BY CATEGORY (valid records)
  ├─ APPOINTMENT .................. <count>  (<pct>%)
  ...

BREAKDOWN BY STATUS (valid records)
  ├─ OPEN ......................... <count>  (<pct>%)
  ├─ CLOSED ....................... <count>  (<pct>%)
  └─ DISCARDED .................... <count>  (<pct>%)

SATISFACTION INDEX (closed cases)
  Scored cases: <n> of <closed_total>
  Average score: <avg> / 5.00
  ├─ Score 1 (Very dissatisfied) ... <count>
  ...

============================================================
Export results to CSV? [y / n]:
```

Optional block (recommended):

```
BREAKDOWN BY COUNTRY (valid records)
  ├─ US ........................... <count>  (<pct>%)
  └─ UK ........................... <count>  (<pct>%)
```

Place the country block after status and before satisfaction, matching `context/05_CONTEXT.md`.

### 3.8 CSV export prompt

At the end of execution, after printing the summary, prompt the user:

```
Export results to CSV? [y / n]:
```

Behaviour:

- Accept `y` or `n` (case-insensitive is fine).
- If **`y`**: write `results.csv` to the current working directory.
- If **`n`**: exit without writing a file.

#### `results.csv` format

One row per metric. Columns:

| Column | Description |
| --- | --- |
| `metric` | Stable snake_case or dotted identifier (e.g. `total_records`, `category.appointment`, `invalid.missing_patient_id`, `satisfaction.average`) |
| `value` | Numeric count or average as a number (no `%` suffix in the value column) |
| `percentage` | Optional; include for breakdown rows where a percentage was shown in the console (one decimal place, no `%` sign, e.g. `31.9`) |

Do **not** export `patient_id`, free-text descriptions, or any row-level PHI. Export aggregate metrics only.

Example rows (illustrative):

```csv
metric,value,percentage
total_records,100,
valid_records,94,
invalid_records,6,
category.appointment,30,31.9
status.closed,52,55.3
satisfaction.average,3.58,
```

---

## 4. Implementation Notes

### 4.1 Suggested module structure

Keep Phase 1 in a single entry file unless complexity warrants helpers:

```text
/
├── pyproject.toml      # Python dependencies (uv)
├── uv.lock             # Locked versions — commit
├── scripts/
│   ├── analyze.py      # CLI entry point, orchestration
│   └── README.md       # Usage and uv commands
```

Logic may be organised internally as functions, e.g.:

- `load_incidents(path) -> DataFrame`
- `validate_record(row) -> list[str]` (rule keys triggered)
- `compute_metrics(valid_df, invalid_counts, total) -> dict`
- `print_report(metrics, source_file)`
- `export_csv(metrics, path)`
- `main()`

### 4.2 Compliance checklist

- [ ] No `patient_id` value in stdout, stderr, or `results.csv`
- [ ] No raw `description` text in error or debug output
- [ ] Invalid-record reporting uses rule labels and counts only
- [ ] Script runs offline with no external API calls

### 4.3 Verification command

```bash
uv sync
uv run python scripts/analyze.py scripts/incidents.csv
```

Compare all required numeric output against §6. Re-run after changes until every value matches.

---

## 5. Acceptance Criteria — Phase 1

### Python environment (uv)

- [ ] Root `pyproject.toml` declares Python 3.12+ and project dependencies (e.g. `pandas`).
- [ ] `uv.lock` is committed; dependencies are installed with `uv sync` — no `requirements.txt`.
- [ ] Scripts run via `uv run python scripts/<script>.py ...`.

### Script & CLI

- [ ] Create the main script (`scripts/analyze.py`) that accepts the path to the CSV as a command-line argument: `uv run python scripts/analyze.py scripts/incidents.csv`.
- [ ] The script loads and reads the file (pandas recommended; standard-library `csv` acceptable).

### Validation

- [ ] Detect and count invalid records.
- [ ] Report how many records fall into each rule type (missing field, out-of-range value, country/clinic mismatch, etc.) without exposing PHI.

### Metrics (valid records unless noted)

- [ ] Total number of elements processed (valid and invalid separately).
- [ ] Breakdown by incident category (`APPOINTMENT`, `BILLING`, `CLINICAL_CARE`, `ACCESSIBILITY`, `ADMINISTRATIVE`).
- [ ] Breakdown by status (`OPEN`, `CLOSED`, `DISCARDED`).
- [ ] Average satisfaction index for closed valid cases that have a recorded score, plus score distribution.

### Output

- [ ] Print the summary to the console in a readable format: separators, clear labels, and alignment.
- [ ] At the end of execution, ask the user: `Export results to CSV? [y / n]`. If they choose `y`, save the results to `results.csv` (one row per metric).
- [ ] Verify that the results match exactly the expected values in §6 when run against `scripts/incidents.csv`.

---

## 6. Expected Results — `scripts/incidents.csv`

When the script runs correctly against the provided test file, required sections must produce **exactly** these values:

### Totals

| Metric | Expected |
| --- | --- |
| Total records in file | 100 |
| Valid records | 94 |
| Invalid / incomplete | 6 |

### Invalid records breakdown

| Rule | Count |
| --- | --- |
| Invalid or missing `clinic_id` | 1 |
| Country/clinic mismatch | 1 |
| Invalid or missing `category` | 1 |
| Empty or too-short `description` | 1 |
| Missing `patient_id` | 1 |
| `CLOSED` with no `satisfaction_score` | 1 |
| Out-of-range `satisfaction_score` | 0 |

### Category breakdown (valid records)

| Category | Count | Percentage |
| --- | --- | --- |
| `APPOINTMENT` | 30 | 31.9% |
| `BILLING` | 20 | 21.3% |
| `CLINICAL_CARE` | 14 | 14.9% |
| `ACCESSIBILITY` | 17 | 18.1% |
| `ADMINISTRATIVE` | 13 | 13.8% |

### Status breakdown (valid records)

| Status | Count | Percentage |
| --- | --- | --- |
| `OPEN` | 28 | 29.8% |
| `CLOSED` | 52 | 55.3% |
| `DISCARDED` | 14 | 14.9% |

### Country breakdown (valid records) — recommended

| Country | Count | Percentage |
| --- | --- | --- |
| `US` | 61 | 64.9% |
| `UK` | 33 | 35.1% |

### Satisfaction index (closed valid records)

| Metric | Expected |
| --- | --- |
| Scored cases | 52 of 52 |
| Average score | 3.58 |

| Score | Count |
| --- | --- |
| 1 | 3 |
| 2 | 5 |
| 3 | 12 |
| 4 | 23 |
| 5 | 9 |

---

## 7. Out of Scope (Phase 1)

- Phase 2 deliverables (to be specified in a separate spec document)
- Web UI or dashboard integration (`uis/backoffice` incident views)
- Database persistence or API endpoints
- Automated tests (optional unless added in a later phase)
- Processing the full 1,000-row production archive (use `scripts/incidents.csv` for development and grading)
- Sending data to external AI services or third-party analytics

---

## 8. References

- `context/05_CONTEXT.md` — authoritative schema, rules, sample output, stakeholder notes
- `scripts/incidents.csv` — verification dataset
- `pyproject.toml` / `uv.lock` — Python dependency manifest (uv)
- `scripts/README.md` — scripts folder conventions
- `04_SPECS.md` — prior milestone spec format reference
