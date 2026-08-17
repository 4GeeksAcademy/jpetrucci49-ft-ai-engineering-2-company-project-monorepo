# SPECS — Milestone 10 Extra (API-042 + FE-019): Backoffice API & Frontend Utility Tests

Implementation specification for **optional follow-on test coverage** after AUTH-088 (M10 core) is complete.

**Tickets:**

| ID | Title | Priority |
| --- | --- | --- |
| API-042 | Unit tests for backoffice endpoints | Low |
| FE-019 | Unit tests for frontend utility functions | Low |

**Prerequisite:** M10 core complete — pytest suite in `services/api/tests/`, Jest configured at repo root for `packages/shared/auth/`, and `TESTING.md` documenting auth runs and coverage. Read `specs/10_SPECS.md` (if present) and [`TESTING.md`](../TESTING.md) before starting.

**Relationship to AUTH-088:** Reuse the same testing infrastructure and principles. Do **not** duplicate auth tests. Extend coverage to **non-authentication** backoffice API logic and **Next.js app utility helpers**.

This milestone adds tests and documentation only. **Do not change production behaviour** unless a test reveals a bug — fix the bug, then log it in `TESTING.md` § Bugs found during testing.

---

## 1. Objective

Close two backlog items while pytest/Jest are already wired up:

1. **API-042** — pytest coverage for at least **two non-auth endpoint groups** in `services/api/`, using the same happy / edge / failure structure as auth tests.
2. **FE-019** — Jest coverage for at least **three pure utility functions** in a Next.js frontend app, with one happy-path and one failure-mode test per function.

Update [`TESTING.md`](../TESTING.md) with run commands, case lists, and coverage results for both extra suites.

---

## 2. Required Reading

| File | Use |
| --- | --- |
| [`TESTING.md`](../TESTING.md) | Existing auth plan — **extend**, do not replace |
| `specs/05_SPECS_INT.md` | Incident analysis API and shared `analysis.py` module |
| `specs/05_SPECS_SCRIPT.md` | CSV schema, validation rules, expected metrics |
| `context/05_CONTEXT.md` | Incident domain rules, PHI constraints |
| `context/06_CONTEXT.md` | Supplier model, categories, country–currency pairing |
| `services/api/routes/suppliers.py` | Supplier CRUD handlers (thin — test underlying logic) |
| `services/api/app/incidents/analysis.py` | Primary incident logic under test |
| `services/api/models.py` | Supplier Pydantic models and validation |
| `uis/talent-pipeline-tracker/lib/validation.ts` | Recommended FE utility targets |
| `uis/talent-pipeline-tracker/lib/labels.ts` | Optional additional FE targets |
| `uis/website/lib/validation.ts` | Alternative FE targets (public enquiry form) |
| `AGENTS.md` | Pre-commit workflow |

---

## 3. Deliverables

| Item | Path |
| --- | --- |
| Supplier pytest module | `services/api/tests/test_suppliers.py` |
| Incident pytest module | `services/api/tests/test_incidents.py` |
| Shared fixtures (if needed) | extend `services/api/tests/conftest.py` |
| Frontend Jest tests | `uis/talent-pipeline-tracker/__tests__/*.test.ts` (recommended app) |
| Jest config for frontend app | `uis/talent-pipeline-tracker/jest.config.mjs` **or** root `jest.config.mjs` project entry |
| npm script | `uis/talent-pipeline-tracker/package.json` → `"test": "jest"` |
| Documentation | `TESTING.md` — new sections for API-042 and FE-019 |

---

## 4. Scope

### 4.1 API-042 — Non-authentication endpoint groups (pick these two)

HealthCore's backoffice API exposes auth (already covered in M10) plus **suppliers** and **incidents**. Test both.

| Endpoint group | Router / module | Test via |
| --- | --- | --- |
| **Suppliers** | `routes/suppliers.py`, `models.py`, `database.py` | `test_suppliers.py` — service/model logic and route decisions without HTTP serialisation |
| **Incidents** | `app/incidents/analysis.py`, optionally `app/incidents/store.py` | `test_incidents.py` — validation, aggregation, PHI-safe error paths |

**Do not test:** auth routes, Next.js BFF handlers, live file uploads via TestClient-only suites, OpenAPI shape assertions.

**Do test:** business decisions — duplicate supplier names, invalid category/country/currency pairs, positive `monthly_rate`, suspension vs deletion semantics, incident row validation rule keys, `analyze()` metric totals on fixture CSV, in-memory store overwrite/empty behaviour.

### 4.2 FE-019 — Frontend utility functions (minimum three)

Pick **pure functions** (no React components, no network). Recommended primary target:

**App:** `uis/talent-pipeline-tracker/`

| Module | Functions | Why |
| --- | --- | --- |
| `lib/validation.ts` | `validateRecordForm`, `hasFieldErrors`, `validateNoteContent` | Form validators used on every candidate registration and note — silent UI bugs if broken |

**Alternative app:** `uis/website/lib/validation.ts` — `validateEnquiryForm` is one large function; if used, add focused tests per validation concern (email, phone, insurance fields) as separate `it(...)` blocks, but still count as one function with multiple happy/failure cases.

**Out of scope for FE-019:** `packages/shared/auth/` (covered in M10), React components, API route handlers, `@healthcore/utils` (covered by root Vitest in `tests/utils/`).

Per function: **≥ 1 happy-path + ≥ 1 failure-mode** test.

---

## 5. Project layout (target)

```text
TESTING.md                                    ← extend with § API-042 and § FE-019
services/api/tests/
  conftest.py                                 ← add suppliers_db fixture if needed
  test_suppliers.py                           ← API-042
  test_incidents.py                           ← API-042
  … (existing auth modules unchanged)

uis/talent-pipeline-tracker/
  __tests__/
    validation.test.ts
    labels.test.ts                            ← optional fourth module
  jest.config.mjs                             ← or root jest "projects" entry
  package.json                                ← "test": "jest"
```

---

## 6. Stack and configuration

### 6.1 Python (reuse M10 setup)

| Item | Value |
| --- | --- |
| Runner | pytest (already in `services/api/pyproject.toml` dev group) |
| Coverage target | ≥ **60%** on modules under test (`models` supplier helpers, `app/incidents/analysis.py`, supplier persistence helpers) |
| DB isolation | Temp `SUPPLIERS_DB_PATH` or reuse pattern from auth — **never mutate dev `suppliers.json`** |
| Incident fixtures | Load bytes from `scripts/incidents.csv` or minimal inline CSV strings in tests |

Add supplier fixture to `conftest.py`:

```python
@pytest.fixture(autouse=True)
def suppliers_db(tmp_path, monkeypatch):
    db_path = tmp_path / "suppliers.json"
    monkeypatch.setenv("SUPPLIERS_DB_PATH", str(db_path))  # match actual env key in database.py
    # reset module-level DB singleton if applicable
    yield
```

Verify the actual env var name in `services/api/database.py` before implementing.

### 6.2 TypeScript (Jest in frontend app)

| Item | Value |
| --- | --- |
| Runner | Jest (reuse root devDependencies or add to app `package.json`) |
| Environment | `node` (validation/labels need no jsdom) |
| Command | `npm run test --prefix uis/talent-pipeline-tracker` |

Example `jest.config.mjs` for the tracker app:

```javascript
export default {
  preset: "ts-jest/presets/default-esm",
  testEnvironment: "node",
  roots: ["<rootDir>/__tests__"],
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/$1" },
  extensionsToTreatAsEsm: [".ts"],
  transform: {
    "^.+\\.tsx?$": ["ts-jest", { useESM: true, tsconfig: { module: "ES2020", paths: { "@/*": ["./*"] } } }],
  },
};
```

Document the final command in `TESTING.md`.

---

## 7. Testing principles (same as AUTH-088)

| Do | Don't |
| --- | --- |
| Assert validation outcomes, rate updates, analysis counts | Assert JSON key order or status codes alone |
| Test `analysis.py` functions directly | Re-test pandas CSV parsing edge cases already in Phase 1 script tests unless API wrapper adds logic |
| Use fixture CSV with **no PHI in assertions** | Log or assert `patient_id` / row-level `description` |
| Mock nothing for pure validators (FE) | Mount React components in Jest |

---

## 8. Planned test cases

Implement **at minimum** one happy-path, one edge-case, and one failure-mode test per endpoint group (API). Map IDs in test names or docstrings. **Copy the tables below into `TESTING.md`** when implementing.

### Suppliers — `test_suppliers.py`

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| SP1 | Happy | Valid supplier create → persisted with `active` status, correct currency for country | Baseline registry flow |
| SP2 | Edge | Update monthly rate → `updated_at` changes | Finance tracking |
| SP3 | Edge | Suspend supplier → status `suspended`, row retained | Regulatory history |
| SP4 | Failure | Duplicate name (if enforced) or invalid category → rejected | Data integrity |
| SP5 | Failure | USA supplier with `GBP` or non-positive rate → model/route rejection | Country–currency invariant |
| SP6 | Failure | GET by missing id → not found path | Invalid lookup |

### Incidents — `test_incidents.py`

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| IN1 | Happy | `analyze()` on valid fixture CSV → expected totals (`total`, `valid_count`, `invalid_count`) | Core reporting path |
| IN2 | Edge | Row with multiple validation failures → counted in invalid breakdown by rule key | Multi-rule handling |
| IN3 | Edge | Store overwrite — second successful analysis replaces first export snapshot | Backoffice “last result” behaviour |
| IN4 | Failure | `validate_record` / loader rejects missing required column | Safe upload rejection |
| IN5 | Failure | Export/store when empty → not-found path | No crash on cold start |
| IN6 | Failure | Assert error paths never include `patient_id` or free-text description | **PHI compliance** |

Use metrics from `specs/05_SPECS_SCRIPT.md` §6 when asserting against `scripts/incidents.csv`.

### Frontend — `uis/talent-pipeline-tracker/__tests__/`

| ID | Function | Happy | Failure |
| --- | --- | --- | --- |
| FE1 | `validateRecordForm` | Complete valid payload → empty errors | Missing email → `errors.email` set |
| FE2 | `hasFieldErrors` | Empty errors object → `false` | Non-empty errors → `true` |
| FE3 | `validateNoteContent` | Non-empty trimmed content → `null` | Whitespace-only → error message |
| FE4 | `getStatusLabel` (optional) | Known status → display label | Unknown string → passthrough |

---

## 9. Test infrastructure notes

### Suppliers

- Seed data lives in `context/06_CONTEXT.md` — use small inline payloads in tests, not the full 15-row seed unless needed.
- If routes delegate to inline DB access, test through the same functions the routes call; extract helpers only if routes are too thick to unit test otherwise.
- Protected routes require auth in production — **API-042 tests logic**, not JWT middleware. Pass `allow_role_change`-style flags or call service functions directly, mirroring M10 auth approach.

### Incidents

- Prefer `load_incidents_from_bytes()` + `analyze()` over reading `scripts/incidents.csv` from disk when possible; use repo fixture path when integration fidelity matters.
- Never assert on raw invalid row content — only rule keys and counts.

### Frontend

- Import from `@/lib/validation` using Jest `moduleNameMapper` aligned with the app's `tsconfig.json` paths.
- Keep tests synchronous — no `render()` from Testing Library unless scope expands (it should not for FE-019).

---

## 10. Quality gates

Run before marking extra milestone complete:

```bash
# API — all tests (auth + new modules)
cd services/api && uv run pytest
uv run pytest --cov=app/incidents --cov-report=term-missing   # ≥ 60% on analysis module
uv run pytest --cov=models --cov-report=term-missing          # supplier model coverage, if split

# Frontend — tracker utilities only
npm run test --prefix uis/talent-pipeline-tracker
```

From repo root:

```bash
uv run --directory services/api pytest tests/test_suppliers.py tests/test_incidents.py
npm run test --prefix uis/talent-pipeline-tracker
```

Also confirm existing auth suite still passes:

```bash
cd services/api && uv run pytest tests/test_register.py  # spot-check
npm run test:auth                                        # if configured at root for shared auth
```

---

## 11. Acceptance checklist

### API-042

- [ ] `test_suppliers.py` and `test_incidents.py` added under `services/api/tests/`
- [ ] ≥ 3 tests per endpoint group (happy, edge, failure)
- [ ] ≥ **60%** coverage on tested modules (`app/incidents/analysis.py` and supplier-related code)
- [ ] Isolated DB / fixtures — dev `suppliers.json` not mutated
- [ ] No PHI in incident test assertions
- [ ] `uv run pytest` passes (full suite)

### FE-019

- [ ] `__tests__/` directory inside chosen frontend app
- [ ] ≥ 3 utility functions tested (happy + failure each)
- [ ] `npm run test --prefix uis/<app>` passes
- [ ] No duplicate coverage of `packages/shared/auth/` or `tests/utils/`

### Documentation

- [ ] `TESTING.md` updated with:
  - Run commands for supplier/incident pytest and frontend Jest
  - Case ID tables (§8 above)
  - Coverage percentages after implementation
- [ ] `memory-bank/progress.md` notes API-042 and FE-019 completion

---

## 12. Hard constraints

| Rule | Detail |
| --- | --- |
| Logic only | No HTTP serialisation or framework internals |
| Isolation | Temp TinyDB / fixtures — never mutate dev JSON databases |
| PHI | Incident tests must not expose `patient_id` or row descriptions |
| Coverage floor | **60%** on API modules under test (lower bar than auth's 70%) |
| No scope creep | Do not refactor unrelated routes or UI |
| Auth unchanged | Do not modify M10 auth tests except shared `conftest.py` extensions |
| Protected paths | Do not edit `context/**` or `.github/**` |

---

## 13. Out of scope

- E2E or Playwright tests
- BFF route handlers in `uis/backoffice/app/api/`
- CI pipeline changes (unless programme already requires)
- Testing `@healthcore/utils` (already covered by root Vitest)
- Testing React components, hooks, or pages
- Live network or file-system uploads in pytest

---

## 14. Suggested agent workflow

1. Read M10 `TESTING.md` and run existing suites to confirm green baseline.
2. Inspect `database.py` for supplier DB path env var; add fixture.
3. Implement `test_suppliers.py` against model + persistence logic; run with coverage.
4. Implement `test_incidents.py` against `analysis.py` (+ store if applicable); verify PHI rules.
5. Add Jest config and `__tests__/` to talent tracker (or chosen app); wire `npm run test`.
6. Append API-042 / FE-019 sections to `TESTING.md` with commands and coverage numbers.
7. Update `memory-bank/progress.md`.

If blocked on env var names or module layout, read the live files under `services/api/` — paths above match the HealthCore monorepo layout from M5–M6.
