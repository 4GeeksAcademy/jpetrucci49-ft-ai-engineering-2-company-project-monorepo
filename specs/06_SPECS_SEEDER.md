# SPECS — Milestone 6 (Step 2): Supplier Directory Seeder

Implementation specification for loading the initial HealthCore supplier directory into TinyDB. Build exactly what is described below.

This is **step 2 of 4** for the Supplier Directory (FastAPI + TinyDB + Pydantic). Step 1 (`models.py`) is complete. Steps 3–4 will cover API routes and the frontend.

---

## 1. Objective

Provide a repeatable seed command that loads the **15 suppliers** defined in `context/06_CONTEXT.md` into TinyDB, validated through the Step 1 Pydantic models. The seeder must be **idempotent** — safe to run multiple times without creating duplicate records.

---

## 2. Required Reading

| File | Use |
| --- | --- |
| `context/06_CONTEXT.md` | `SUPPLIERS_SEED` payload (§ Seeder initial data) |
| `specs/06_SPECS_DATA.md` | `SupplierCreate`, `Supplier`, `updated_at` rules |

---

## 3. Project Layout (This Step)

```text
services/
  api/
    models.py            ← Step 1 (complete)
    database.py          ← TinyDB initialisation (this step)
    seed.py              ← initial data loading script (this step)
    pyproject.toml       ← add `uv run seed` script entry
```

Out of scope here: `main.py`, `routes/suppliers.py`, frontend.

---

## 4. Stack & Command

| Item | Value |
| --- | --- |
| Package manager | **uv** (`services/api/pyproject.toml`) |
| Storage | [TinyDB](https://tinydb.readthedocs.io/) |
| Seed command | `uv run seed` (from `services/api/`) |

Add TinyDB to `services/api/pyproject.toml` dependencies and register the seed script so **`uv run seed`** executes `seed.py` without extra arguments.

---

## 5. `database.py`

Initialise a single TinyDB instance for supplier records.

| Requirement | Detail |
| --- | --- |
| Database file | JSON file under `services/api/` (e.g. `suppliers.json`) — path configurable via env var with a sensible default |
| Table name | One table for suppliers (e.g. `"suppliers"`) |
| Gitignore | Database file must be gitignored (not committed) |
| Exports | Functions the seeder and later routes can import — e.g. `get_suppliers_table()` |

Persist documents in a shape compatible with the `Supplier` response model (`id`, all base fields, `updated_at`).

---

## 6. Seed Data

Define `SUPPLIERS_SEED` in `seed.py` (or a dedicated `seed_data.py` module imported by `seed.py`) as a list of dicts matching **`context/06_CONTEXT.md` exactly** — same 15 suppliers, field names, and values.

Do not alter names, rates, categories, or statuses from the context. Optional fields omitted in the context (`contract_renewal_date`, `notes`, `compliance_agreement`) remain absent or `null` as given.

---

## 7. Seeding Behaviour

### 7.1 Validation before insert

For each seed entry:

1. Parse through `SupplierCreate` — invalid seed data must raise at development time, not silently corrupt the database.
2. Assign `updated_at` = current UTC datetime (per `06_SPECS_DATA.md` §8 — same as create).
3. Insert into TinyDB and assign `id` from the TinyDB document id.

### 7.2 Idempotency (no duplicates)

Running the seeder more than once **must not** insert duplicate suppliers.

Recommended approach (pick one, document in code):

| Strategy | Behaviour on re-run |
| --- | --- |
| **Skip when populated** | If the suppliers table already contains records, insert nothing |
| **Upsert by natural key** | Match on `name` + `country`; insert only missing suppliers |

Either way, a second consecutive run inserts **0** new records when data is already present.

### 7.3 Console output

On completion, print a clear summary to stdout, for example:

```text
Seeder finished: 15 supplier(s) inserted (15 total in database).
```

| Run | Expected output pattern |
| --- | --- |
| First run (empty DB) | Confirms **15 inserted** and **15 total** |
| Second run (already seeded) | Confirms **0 inserted** and **15 total** |

The inserted count and total count must both appear when the command finishes.

### 7.4 Exit code

- `0` on success
- Non-zero on validation failure, I/O error, or unexpected exception (with a readable error message on stderr)

---

## 8. Acceptance Checklist

- [ ] `uv run seed` runs without errors and loads the CONTEXT suppliers into the database.
- [ ] Running the seeder more than once does not produce duplicates.
- [ ] The number of records inserted is confirmed in the console when it finishes.
- [ ] All 15 seed records validate through `SupplierCreate` before insert
- [ ] Each stored record includes system-generated `id` and `updated_at`
- [ ] `database.py` initialises TinyDB; database file is gitignored
- [ ] `SUPPLIERS_SEED` matches `context/06_CONTEXT.md` verbatim

---

## 9. Verification

From `services/api/`:

```bash
uv sync
uv run seed          # expect: 15 inserted, 15 total
uv run seed          # expect: 0 inserted, 15 total
```

Optionally inspect the JSON file or query via a REPL to confirm 15 distinct records with expected `name` values.

---

## 10. Out of Scope (Later Steps)

- REST endpoints in `routes/suppliers.py`
- Mounting supplier routes in `main.py`
- Frontend directory page
- Deleting or truncating via API (suppliers are suspended, not deleted)
