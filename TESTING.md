# HealthCore API — Authentication Testing (AUTH-088)

**Ticket:** AUTH-088 — Unit test coverage for the authentication API  
**Spec:** [`specs/10_SPECS.md`](specs/10_SPECS.md)

This document lives at the **monorepo root** (`TESTING.md`) and is the **test plan and testing guide** for the FastAPI authentication module (`services/api/`). Tests assert **business logic** — what the application *decides* — not HTTP serialisation or framework plumbing.

---

## How to run tests

### FastAPI (pytest)

From the FastAPI project root (`services/api/`):

```bash
cd services/api
uv sync --group dev          # install pytest + pytest-cov
uv run pytest                # run all tests
uv run pytest -v             # verbose
uv run pytest --cov=auth --cov-report=term-missing   # coverage report
```

From the monorepo root:

```bash
uv run --directory services/api pytest
uv run --directory services/api pytest --cov=auth --cov-report=term-missing
```

**Coverage target:** ≥ **70%** on the `auth/` package (`uv run pytest --cov=auth`).

Tests use an isolated TinyDB file (`AUTH_DB_PATH` temp dir) and `HEALTHCORE_API_TEST=1` — they do **not** read your development `auth.json` or call Resend.

### TypeScript (Jest)

Authentication-related client helpers live in `packages/shared/auth/`. Configure Jest at the monorepo root (or a dedicated package config) and run:

```bash
npm install                    # includes jest + ts-jest (when configured)
npx jest --coverage
```

See [§ TypeScript test suites](#typescript-test-suites-jest) below.

---

## Testing principles

| Do | Don't |
| --- | --- |
| Assert password hashing, token expiry, role checks, duplicate users | Assert JSON field order or status codes alone |
| Test services (`auth/services/`), security (`auth/security.py`), dependencies | Test FastAPI middleware or Pydantic serialisation |
| Mock `send_password_reset_email` | Call Resend in tests |
| Use temp TinyDB per test | Mutate developer `auth.json` |

**Examples of business-logic questions we answer:**

- Does a valid login produce a JWT whose `sub` matches the user id?
- Does an **expired** JWT fail `decode_access_token`?
- Does **forgot-password** skip email for unknown addresses (no enumeration)?
- Can a reset token be used **twice**?
- Is a **duplicate email** rejected on register?
- Can a non-admin **change roles**?

---

## Test suite layout

```text
TESTING.md                 ← this file (plan + how-to)
services/api/
  tests/
    conftest.py              ← shared fixtures (temp DB, users, mocks)
    test_register.py         ← POST /users
    test_login.py            ← POST /auth/login (credential + JWT logic)
    test_token.py            ← JWT + reset token security helpers
    test_me.py               ← GET /auth/me + get_current_user
    test_forgot_password.py  ← POST /auth/forgot-password
    test_reset_password.py   ← POST /auth/reset-password
    test_change_password.py  ← POST /auth/change-password
    test_users_admin.py      ← GET/PUT/DELETE /users, GET /users/{id}
    test_profiles.py         ← GET/PUT /profiles/me
    test_dependencies.py     ← require_admin, require_self_or_admin
```

| Module | Endpoints / logic covered | Why these cases |
| --- | --- | --- |
| `test_register.py` | `POST /users` | Registration is the entry point; duplicates and normalisation caused past data bugs |
| `test_login.py` | `POST /auth/login` | Core auth gate — wrong password, inactive users must never receive a token |
| `test_token.py` | `auth/security.py` | Central crypto/JWT — expiry and tampering are high-risk regression areas |
| `test_me.py` | `GET /auth/me` | Validates token → user → profile chain |
| `test_forgot_password.py` | `POST /auth/forgot-password` | Must not leak whether an email exists |
| `test_reset_password.py` | `POST /auth/reset-password` | Single-use + expiry tokens are security-critical |
| `test_change_password.py` | `POST /auth/change-password` | Authenticated password change must verify current password |
| `test_users_admin.py` | `/users`, `/users/{id}` | Admin vs self authorization and CRUD |
| `test_profiles.py` | `/profiles/me` | Profile updates and empty-body rejection |
| `test_dependencies.py` | Shared deps | 401/403 decisions reused by many routes |

---

## Planned test cases (by endpoint)

Implement **at minimum** one happy-path, one edge-case, and one failure-mode test per endpoint. IDs below map to pytest functions when implemented.

### `POST /users` — register (`test_register.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| U1 | Happy | Valid email + password creates user + profile, role `user` | Baseline registration flow |
| U2 | Edge | Omit optional name → default from email local-part | Documents expected default behaviour |
| U3 | Edge | Email with spaces / mixed case → stored lowercase | Prevents duplicate accounts by casing |
| U4 | Failure | Duplicate email → `ValueError` | Common user error; must not overwrite |
| U5 | Failure | Password too short (model validation) | Boundary on minimum password length |

### `POST /auth/login` (`test_login.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| L1 | Happy | Valid credentials → JWT decodes to user id | Core login success path |
| L2 | Edge | Lookup with mixed-case email after lowercase register | Email normalisation at login |
| L3 | Failure | Wrong password → must not produce valid token | Prevents auth bypass |
| L4 | Failure | Unknown email → no user | Same generic failure as wrong password at route |
| L5 | Failure | Inactive user → must not login | Deactivated accounts stay locked out |

### `GET /auth/me` (`test_me.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| M1 | Happy | Valid token + profile exists → user + profile data | Happy read path |
| M2 | Edge | Role changed in DB after token issued → `/me` sees new role | JWT is stateless; role comes from DB |
| M3 | Failure | Malformed / invalid JWT | Token validation must fail closed |
| M4 | Failure | User deleted or deactivated after token issued | Stale tokens must not grant access |
| M5 | Failure | Profile missing for user | Orphan user handling |

### `POST /auth/forgot-password` (`test_forgot_password.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| F1 | Happy | Active user → reset token row + email mock called | Confirms token issuance path |
| F2 | Edge | Unknown email → no token, no email (silent no-op) | **Anti-enumeration** — critical security requirement |
| F3 | Edge | Inactive user → no token, no email | Inactive accounts cannot reset |
| F4 | Failure | Email provider raises → logged, no crash | Resilience; caller still gets generic success |
| F5 | Edge | Second request invalidates earlier unused token | Prevents multiple valid reset links |

### `POST /auth/reset-password` (`test_reset_password.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| R1 | Happy | Valid token → password updated, `used_at` set | Complete reset flow |
| R2 | Edge | New password at minimum length (8) | Boundary acceptance |
| R3 | Failure | Reuse same token → rejected | **Single-use** tokens |
| R4 | Failure | Expired token → rejected | **Expiry** enforcement |
| R5 | Failure | Random / tampered token string | Invalid hash must not reset password |
| R6 | Failure | Token for inactive user | Account state honoured at reset |

### `POST /auth/change-password` (`test_change_password.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| C1 | Happy | Correct current + new password → stored hash updates | Authenticated change path |
| C2 | Edge | New password equals current → rejected | Prevents no-op "changes" |
| C3 | Failure | Wrong current password | Must not allow change without proof |
| C4 | Failure | Unknown user id | Service fail-closed |

### `GET /users` — admin list (`test_users_admin.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| A1 | Happy | Admin → sorted user list | Admin-only listing |
| A2 | Edge | Empty database → `[]` | No crash on empty table |
| A3 | Failure | Non-admin → 403 via `require_admin` | Authorization boundary |

### `GET /users/{id}` (`test_users_admin.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| G1 | Happy | User reads own record | Self-service access |
| G2 | Happy | Admin reads another user | Admin oversight |
| G3 | Failure | Non-admin reads another user → 403 | Privacy / horizontal privilege |
| G4 | Failure | Missing user id → not found | Invalid id handling |

### `PUT /users/{id}` (`test_users_admin.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| P1 | Happy | Self updates email (normalised) | Self-service profile of credentials |
| P2 | Happy | Admin updates role | Admin promotion path |
| P3 | Edge | Empty update → unchanged user | Idempotent no-op |
| P4 | Failure | Non-admin sets role → `PermissionError` | **Role escalation** guard |
| P5 | Failure | Duplicate email on update | Uniqueness constraint |
| P6 | Failure | Non-admin updates another user → 403 | Authorization |

### `DELETE /users/{id}` (`test_users_admin.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| D1 | Happy | Self delete → user + profile removed | Account closure |
| D2 | Happy | Admin deletes other user | Admin moderation |
| D3 | Failure | Non-admin deletes other → 403 | Authorization |
| D4 | Failure | Missing user → `LookupError` | Invalid target |

### `GET /profiles/me` (`test_profiles.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| PM1 | Happy | User with profile → returns profile | Baseline read |
| PM2 | Failure | Profile missing → not found path | Data integrity |

### `PUT /profiles/me` (`test_profiles.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| PU1 | Happy | Update name → persisted | Basic write |
| PU2 | Edge | Partial update (phone only) → other fields unchanged | PATCH-like behaviour |
| PU3 | Failure | All fields empty / None → rejected before service | Route-level guard |
| PU4 | Failure | Profile not found | Missing data handling |

### Shared — JWT & crypto (`test_token.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| S1 | Happy | `hash_password` / `verify_password` round-trip | Password storage correctness |
| S2 | Happy | `create_access_token` / `decode_access_token` → same user id | Token generation correctness |
| S3 | Edge | Two `generate_reset_token` calls differ | Unpredictable reset secrets |
| S4 | Failure | Expired JWT rejected | **Expired token** regression (ticket example) |
| S5 | Failure | JWT signed with wrong secret | Tampering detection |
| S6 | Happy | `hash_reset_token` is deterministic SHA-256 hex | Lookup consistency |

### Shared — dependencies (`test_dependencies.py`)

| ID | Type | Case | Why included |
| --- | --- | --- | --- |
| Dp1 | Happy | `get_current_user` + valid token + active user | Auth gate success |
| Dp2 | Failure | Inactive user → 401 | Deactivation honoured |
| Dp3 | Happy | `require_admin` passes for admin | Admin routes |
| Dp4 | Failure | `require_admin` 403 for regular user | Admin boundary |
| Dp5 | Happy | `require_self_or_admin` for self | Self access |
| Dp6 | Happy | `require_self_or_admin` admin on other id | Admin override |
| Dp7 | Failure | `require_self_or_admin` user on other id → 403 | Horizontal privilege |

---

## Regression risks explicitly covered

| Risk | Test IDs |
| --- | --- |
| Reset token reuse | R3 |
| Email enumeration on forgot-password | F2, F3 |
| Non-admin role escalation | P4 |
| JWT still works after deactivation | L5, Dp2 |
| Stale reset link after newer request | F5 |
| Plain-text password in database | U1, S1 |
| Expired JWT accepted | S4 |

---

## TypeScript test suites (Jest)

Target: `packages/shared/auth/` — client-side auth **logic** (not React components).

| Module | Functions | Planned cases | Why |
| --- | --- | --- | --- |
| `errors.ts` | `parseApiError`, `parseApiFieldErrors` | Happy: string `detail`; Failure: non-JSON body | Login/register forms depend on error text |
| `token.ts` | `getToken`, `setToken`, `clearToken` | Happy: round-trip in jsdom; Failure: logout clears cookie + localStorage on localhost | Session lifecycle |
| `cross-app.ts` | `buildAuthenticatedAppUrl`, `consumeTokenFromHash` | Happy: appends hash when token present; Failure: missing hash returns false | Cross-app session handoff |

Per function: **≥ 1 happy-path + ≥ 1 failure-mode** test.

> **Note:** The monorepo root currently uses Vitest for M2 utilities. AUTH-088 asks for Jest — add `jest.config.ts` at repo root (or under `packages/shared/`) when implementing TS tests. Document the final command here once configured.

---

## AI-assisted workflow

1. **Plan first** — cases listed in this file before writing tests (§ Planned test cases).
2. **Generate boilerplate** — use an AI agent to scaffold pytest/Jest files from the tables above.
3. **Review every test** — confirm each assertion targets business logic, not HTTP shape.
4. **Prompt for gaps** — ask the agent: *“Given this endpoint logic, what edge cases am I missing?”*
5. **Fix bugs found by tests** — document below.

---

## Bugs found during testing

| Date | Test | Bug | Fix |
| --- | --- | --- | --- |
| _—_ | _—_ | _None yet — populate when tests reveal issues_ | _—_ |

---

## Implementation checklist

### Test plan (this document)

- [x] `TESTING.md` at monorepo root
- [x] Cases listed: happy path, edge cases, failure modes per endpoint
- [x] Rationale documented for each suite and risk area

### FastAPI — pytest

- [ ] `tests/` directory with `conftest.py`
- [ ] One module per endpoint group (see layout above)
- [ ] ≥ 3 tests per endpoint (happy, edge, failure)
- [ ] `uv run pytest` passes
- [ ] `uv run pytest --cov=auth` ≥ **70%**

### TypeScript — Jest

- [ ] Jest configured (`jest.config.ts` or `.js`)
- [ ] Tests for `packages/shared/auth/` helpers
- [ ] `jest --coverage` passes

### AI workflow

- [ ] Agent used to review case list for gaps
- [ ] All generated tests reviewed before commit
- [ ] Any bugs found documented in § Bugs found during testing

---

## Out of scope

- HTTP serialisation / OpenAPI contract tests
- Live Resend email delivery
- Supplier and incident endpoints
- Next.js BFF route handlers
- End-to-end browser tests
