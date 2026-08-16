# SPECS — Milestone 10 (AUTH-088): Authentication API Unit Tests

Implementation specification for **unit test coverage** of the HealthCore authentication API.

**Ticket:** AUTH-088 — Unit test coverage for the authentication API  
**Prerequisite:** M7–M9 auth complete (`specs/07_SPECS.md` … `specs/09_SPECS_FRONT.md`)  
**Test plan (cases, rationale, run commands):** [`TESTING.md`](../TESTING.md) — **read before writing tests; do not duplicate case tables in code comments**

This milestone adds tests only. **Do not change production auth behaviour** unless a test reveals a bug — fix the bug, then document it in `TESTING.md` § Bugs found during testing.

---

## 1. Objective

Add a comprehensive pytest suite (and Jest suite for TypeScript auth helpers) that validates **business logic** at the function and service layer:

- Token generation, expiry, and rejection of malformed credentials
- Password reset single-use tokens and anti-enumeration on forgot-password
- Role and ownership guards (`admin`, self-or-admin)
- User/profile CRUD invariants (duplicate email, inactive accounts)

**Do not** test HTTP serialisation, OpenAPI shapes, or FastAPI framework internals. Assert what the application **decides**, not how it **responds**.

Minimum per authentication endpoint: **one happy-path**, **one edge-case**, **one failure-mode** test — see [`TESTING.md` § Planned test cases](../TESTING.md#planned-test-cases-by-endpoint) for the authoritative list.

---

## 2. Required Reading

| File | Use |
| --- | --- |
| [`TESTING.md`](../TESTING.md) | Case IDs, suite layout, commands, coverage target, checklist |
| `services/api/routes/auth.py` | Auth endpoints to cover |
| `services/api/routes/users.py` | User CRUD + register |
| `services/api/routes/profiles.py` | Profile endpoints |
| `services/api/auth/security.py` | JWT + password + reset-token helpers |
| `services/api/auth/services/` | Primary logic under test |
| `services/api/auth/dependencies.py` | AuthZ dependencies |
| `packages/shared/auth/` | TypeScript helpers for Jest |
| `AGENTS.md` | Pre-commit workflow |

---

## 3. Deliverables

| Item | Path |
| --- | --- |
| Test plan & run guide | `TESTING.md` (repo root) — **already drafted** |
| pytest suite | `services/api/tests/` |
| Jest config + TS tests | `jest.config.ts` (repo root or `packages/shared/`) + tests alongside `packages/shared/auth/` |
| Dev dependencies | `services/api/pyproject.toml` — pytest, pytest-cov, freezegun |
| Coverage | ≥ **70%** on `auth/` package |

---

## 4. Scope

### 4.1 Authentication endpoints (must cover all 12)

| Router | Endpoints |
| --- | --- |
| `routes/auth.py` | `POST /auth/login`, `GET /auth/me`, `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/change-password` |
| `routes/users.py` | `POST /users`, `GET /users`, `GET/PUT/DELETE /users/{id}` |
| `routes/profiles.py` | `GET /profiles/me`, `PUT /profiles/me` |

### 4.2 Logic modules (test these directly)

| Module | Test via |
| --- | --- |
| `auth/security.py` | `test_token.py` |
| `auth/services/users.py` | `test_register.py`, `test_login.py`, `test_change_password.py`, `test_users_admin.py` |
| `auth/services/profiles.py` | `test_profiles.py`, `test_me.py` (profile load) |
| `auth/services/password_reset.py` | `test_forgot_password.py`, `test_reset_password.py` |
| `auth/dependencies.py` | `test_dependencies.py`, `test_me.py` |

Route handlers stay thin. Prefer **service and security unit tests**. Use dependency tests (with mocked tokens/users) for authorization decisions. Only test route-level logic when it lives exclusively in the handler (e.g. empty profile update body in `routes/profiles.py`).

### 4.3 Out of scope

- Supplier and incident routes
- Next.js BFF handlers
- Live Resend / network I/O
- Pydantic 422 field-list assertions
- E2E or TestClient-only suites that assert status codes without logic

---

## 5. Project layout (target)

```text
TESTING.md                          ← plan + how-to (repo root)
services/api/
  pyproject.toml                    ← add dev dependency group
  tests/
    conftest.py
    test_register.py
    test_login.py
    test_token.py
    test_me.py
    test_forgot_password.py
    test_reset_password.py
    test_change_password.py
    test_users_admin.py
    test_profiles.py
    test_dependencies.py
packages/shared/auth/
  __tests__/                        ← or *.test.ts alongside modules
jest.config.ts                      ← repo root (recommended)
```

File-to-endpoint mapping and case IDs: [`TESTING.md` § Test suite layout](../TESTING.md#test-suite-layout).

---

## 6. Stack and configuration

### 6.1 Python

| Item | Value |
| --- | --- |
| Runner | pytest |
| Coverage | pytest-cov, target package `auth` |
| Time freezing | freezegun (JWT / reset-token expiry) |
| DB | Isolated TinyDB via temp `AUTH_DB_PATH` |

Add to `services/api/pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "freezegun>=1.4",
]
```

Optional `[tool.pytest.ini_options]` in `pyproject.toml`:

```toml
testpaths = ["tests"]
pythonpath = ["."]
```

### 6.2 TypeScript

| Item | Value |
| --- | --- |
| Runner | **Jest** (per ticket) |
| Target | `packages/shared/auth/` — `errors.ts`, `token.ts`, `cross-app.ts` |
| Environment | jsdom for `token.ts` / `cross-app.ts` (localStorage, `document.cookie`, `window.location`) |

Root `npm test` runs **Vitest** for M2 utilities — do not migrate those. Jest is scoped to auth helpers only. Document final Jest commands in `TESTING.md` when configured.

Per function: ≥ 1 happy-path + ≥ 1 failure-mode. Case detail: [`TESTING.md` § TypeScript test suites](../TESTING.md#typescript-test-suites-jest).

---

## 7. Test infrastructure (`conftest.py`)

Implement shared fixtures once; all modules import them.

| Fixture | Behaviour |
| --- | --- |
| `auth_env` | Set `HEALTHCORE_API_TEST=1`, dummy `JWT_SECRET`, `RESET_TOKEN_EXPIRE_MINUTES=30`, `PASSWORD_RESET_URL` |
| `auth_db` | Temp `AUTH_DB_PATH`; reset `auth.database._db = None` before/after |
| `registered_user` | `create_user()` → `(UserInDB, ProfilePublic)` |
| `admin_user` | User with `role=admin` |
| `inactive_user` | User with `is_active=False` |
| `auth_token` | `create_access_token(user_id)` |
| `mock_reset_email` | Patch `auth.services.password_reset.send_password_reset_email` |

**Never** read or write the developer's `services/api/auth.json`. **Never** call Resend in tests.

---

## 8. Implementation rules

1. **Map tests to `TESTING.md` case IDs** — name tests `test_u1_valid_registration` or reference ID in docstring for traceability.
2. **Assert outcomes, not transport** — e.g. `verify_password(new, user.hashed_password)` not `response.status_code == 200`.
3. **Mock external I/O** — email send always patched in forgot-password tests.
4. **Regression priorities** — must include tests for: reset token reuse (R3), forgot-password enumeration (F2/F3), non-admin role change (P4), expired JWT (S4), inactive user login (L5).
5. **Async dependencies** — test `get_current_user`, `require_admin`, `require_self_or_admin` with `pytest.mark.asyncio` and injected/mocked `user_service` where needed.
6. **Bugs** — if a test fails due to production code, fix the code, add/adjust the test, log in `TESTING.md`.

Login credential checks currently live in `routes/auth.py`; cover via `verify_password` + `get_user_by_email` + `create_access_token` integration in `test_login.py` without FastAPI TestClient unless extracting a helper later.

---

## 9. Quality gates

Run before marking milestone complete:

```bash
cd services/api && uv sync --group dev && uv run pytest
uv run pytest --cov=auth --cov-report=term-missing   # ≥ 70%
npx jest --coverage                                   # after Jest configured
```

From repo root: `uv run --directory services/api pytest`

Full command reference: [`TESTING.md` § How to run tests](../TESTING.md#how-to-run-tests).

---

## 10. Acceptance checklist

### Documentation

- [ ] `TESTING.md` at repo root (plan complete — verify checklist items as tests land)

### FastAPI

- [ ] `services/api/tests/conftest.py` with isolated DB fixtures
- [ ] One test module per endpoint group (§5 layout)
- [ ] All 12 endpoints covered with ≥ 3 tests each (happy, edge, failure)
- [ ] `uv run pytest` passes with zero failures
- [ ] `uv run pytest --cov=auth` ≥ **70%**
- [ ] No Resend network calls; `send_password_reset_email` mocked

### TypeScript

- [ ] Jest configured; tests for `packages/shared/auth/` helpers
- [ ] `jest --coverage` passes

### Process

- [ ] Every test reviewed — no serialisation-only assertions
- [ ] Bugs found during testing logged in `TESTING.md`

---

## 11. Hard constraints

| Rule | Detail |
| --- | --- |
| Logic only | No HTTP serialisation or framework internals |
| Isolation | Temp TinyDB per test — never mutate dev `auth.json` |
| Mock email | No live Resend |
| Coverage floor | 70% on `auth/` |
| No scope creep | Do not refactor unrelated auth code |
| Plan is source of truth | Case list lives in `TESTING.md`, not duplicated in spec |

---

## 12. Out of scope

- CI pipeline changes (unless already required by programme)
- Extracting `authenticate_user()` from login route (optional refactor)
- Vitest migration for auth helpers (Jest per ticket)
- Frontend component tests (`uis/*/components/auth/`)
