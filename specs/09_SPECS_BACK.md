# SPECS — Milestone 9 (AUTH-03): Password Recovery and Change — Backend

Implementation specification for **password reset (forgot + reset) and authenticated password change** on the HealthCore FastAPI service.

**Prerequisite:** M7 complete (`specs/07_SPECS.md`).  
**Companion spec:** Frontend flows live in `specs/09_SPECS_FRONT.md` (AUTH-03 phase 2).  
**Out of scope here:** Next.js views, BFF routes, and UI validation — backend only.

This is a **security milestone**. Reset tokens must be short-lived, single-use, and non-enumerable. Email delivery must never leak whether an address is registered.

---

## 1. Objective

Add three auth endpoints and transactional email delivery so internal users can:

| Flow | Endpoint | Caller |
| --- | --- | --- |
| Request reset link | `POST /auth/forgot-password` | Public (unauthenticated) |
| Set new password via email link | `POST /auth/reset-password` | Public (possesses reset token) |
| Change password while logged in | `POST /auth/change-password` | Authenticated (bearer JWT) |

Reset tokens are **opaque, server-tracked secrets** — not reusable JWT access tokens. A token expires within **15–60 minutes** and is **invalidated immediately after a successful reset**.

---

## 2. Required Reading

| File | Use |
| --- | --- |
| `specs/07_SPECS.md` | Existing auth models, JWT, TinyDB layout |
| `services/api/auth/security.py` | Password hash/verify, JWT helpers |
| `services/api/auth/services/users.py` | User lookup and password updates |
| `services/api/routes/auth.py` | Router to extend |
| `services/api/auth/database.py` | TinyDB table pattern |
| `AGENTS.md` | Pre-commit workflow |

---

## 3. Project Layout (target)

```text
services/api/
  auth/
    models.py                      ← add request/response schemas for password flows
    database.py                    ← add password_reset_tokens table accessor
    security.py                    ← add reset-token create/hash/verify helpers
    config.py                      ← email + reset URL + expiry env vars
    services/
      password_reset.py            ← issue token, consume token, send email orchestration
      users.py                     ← add update_password(user_id, new_password) if needed
    email/
      __init__.py
      base.py                      ← EmailSender protocol / shared types
      templates.py                 ← shared HTML + plain-text bodies
      resend_sender.py             ← Resend implementation
  routes/
    auth.py                        ← add forgot / reset / change-password handlers
  .env.example                     ← document new env vars
  pyproject.toml                   ← add resend dependency
```

Email delivery uses **Resend** only. Document setup in `services/api/README.md`.

---

## 4. Stack and Dependencies

| Item | Value |
| --- | --- |
| Framework | FastAPI (existing) |
| Password hashing | Reuse `auth/security.py` — bcrypt via existing `CryptContext` |
| Reset tokens | Cryptographically random opaque string (`secrets.token_urlsafe(32)` or equivalent) |
| Token storage | TinyDB table `password_reset_tokens` — store **hash only**, never the raw token |
| Token hash | SHA-256 hex digest of the raw token (constant-time compare on lookup) |
| Email | **Resend** (`resend` SDK) — free tier sufficient for dev |
| Access tokens | Unchanged — PyJWT bearer tokens from M7 |

Add to `pyproject.toml`:

```toml
"resend>=2.0,<3",
```

Resend supports development sending without a custom domain via its onboarding sender — see [Resend docs](https://resend.com/docs).

---

## 5. Environment Variables

Document every new variable in `services/api/.env.example`. **Never hardcode API keys or sender addresses.**

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `JWT_SECRET` | **Yes** | — | Existing — access token signing |
| `RESET_TOKEN_EXPIRE_MINUTES` | No | `30` | Reset link lifetime (**15–60** allowed range; validate at startup) |
| `PASSWORD_RESET_URL` | **Yes** | — | Frontend reset page base URL **without** query string, e.g. `http://localhost:3001/reset-password` — append `?token=<raw_token>` when building the email link |
| `RESEND_API_KEY` | **Yes** | — | Resend API key |
| `RESEND_FROM_EMAIL` | **Yes** | — | Verified/onboarding sender address |

Startup behaviour:

- Fail fast if `PASSWORD_RESET_URL` is missing in non-test environments.
- Fail fast if `RESEND_API_KEY` or `RESEND_FROM_EMAIL` is missing.
- Reject `RESET_TOKEN_EXPIRE_MINUTES` outside **15–60** (inclusive).

---

## 6. Data Model — `password_reset_tokens` (TinyDB)

New table in the same TinyDB file as users (`auth.json` by default).

| Field | Type | Rules |
| --- | --- | --- |
| `id` | `int` | TinyDB doc id |
| `user_id` | `int` | FK to `users` table |
| `token_hash` | `str` | SHA-256 hex of the raw token — **never store raw token** |
| `expires_at` | `str` (ISO UTC) | Server-set at creation |
| `used_at` | `str \| null` | `null` until consumed; set to ISO UTC on successful reset |
| `created_at` | `str` (ISO UTC) | Server-set at creation |

**Rules:**

- At most one **active** (unused, unexpired) token per user is recommended — invalidate or ignore older tokens when issuing a new one (simplest: mark previous unused tokens as used, or delete them, before insert).
- Raw token exists only in the email link and the client request body — never logged, never persisted.

---

## 7. Request and Response Schemas

Add Pydantic models in `auth/models.py`:

### 7.1 `ForgotPasswordRequest`

| Field | Type | Rules |
| --- | --- | --- |
| `email` | `EmailStr` | Required |

### 7.2 `MessageResponse`

Generic success envelope for non-enumerating endpoints:

```json
{ "message": "If that address is registered, you'll receive a link shortly." }
```

Use this **exact message** (or equivalent approved copy) for every `POST /auth/forgot-password` response.

### 7.3 `ResetPasswordRequest`

| Field | Type | Rules |
| --- | --- | --- |
| `token` | `str` | Required — raw token from email link |
| `new_password` | `str` | Required — `min_length=8` (match registration) |

### 7.4 `ChangePasswordRequest`

| Field | Type | Rules |
| --- | --- | --- |
| `current_password` | `str` | Required |
| `new_password` | `str` | Required — `min_length=8` |

### 7.5 `ChangePasswordResponse`

```json
{ "message": "Password updated successfully." }
```

---

## 8. Reset Token Lifecycle

```text
forgot-password
  → lookup user by email (silent if missing)
  → generate raw token
  → store SHA-256(raw) + user_id + expires_at in TinyDB
  → send email with link: PASSWORD_RESET_URL?token=<raw>

reset-password
  → hash incoming token
  → lookup row by token_hash
  → reject 400 if: not found | expired | used_at is set
  → hash new_password, update user.hashed_password
  → set used_at on token row
  → return 200

change-password
  → get_current_user (401 if no/invalid bearer)
  → verify current_password (400 if wrong)
  → hash new_password, update user
  → return 200
```

**Single-use enforcement:** After a successful `reset-password`, the token row must have `used_at` set. A second request with the same token → **400**.

**Expiry enforcement:** Compare `expires_at` to current UTC before accepting reset. Expired token → **400** with a clear, generic detail (e.g. `"Invalid or expired reset token."`).

Use the **same error detail** for invalid, expired, and already-used reset tokens — do not distinguish between them in the API response (prevents token probing).

---

## 9. REST Endpoints

Extend `routes/auth.py` (prefix `/auth`). Tag: `auth`.

### 9.1 `POST /auth/forgot-password`

| | |
| --- | --- |
| **Auth** | Public |
| **Body** | `ForgotPasswordRequest` |
| **Response** | **200** `MessageResponse` — **always**, whether or not the email exists |

**Behaviour:**

1. Normalize email (same rules as `users.py`).
2. If user **does not exist** or is **inactive** → return **200** with generic message; **do not send email**.
3. If user exists and is active → create reset token, send email, return **200** with the **same** generic message.
4. Email send failures should be logged server-side; still return **200** to the client (do not leak internal errors or account existence).

**Security:** Never return **404** for unknown emails. Never include `"user not found"` in the response body.

### 9.2 `POST /auth/reset-password`

| | |
| --- | --- |
| **Auth** | Public |
| **Body** | `ResetPasswordRequest` |
| **Success** | **200** `MessageResponse` (e.g. `"Password reset successfully."`) |
| **Failure** | **400** — invalid, expired, or already-used token |

**Behaviour:**

1. Hash `token`, lookup in `password_reset_tokens`.
2. Reject **400** if row missing, `used_at` is set, or `expires_at` is in the past.
3. Load user by `user_id`; reject **400** if user missing or inactive (same generic error as invalid token).
4. `hash_password(new_password)` → update user record.
5. Set `used_at` on the token row.
6. Return **200**.

Optional hardening (recommended): invalidate any other unused reset tokens for that user.

### 9.3 `POST /auth/change-password`

| | |
| --- | --- |
| **Auth** | **Protected** — `Depends(get_current_user)` |
| **Body** | `ChangePasswordRequest` |
| **Success** | **200** `ChangePasswordResponse` |
| **Wrong current password** | **400** — e.g. `{ "detail": "Current password is incorrect." }` |
| **Missing/invalid bearer** | **401** (existing `get_current_user` behaviour) |

**Behaviour:**

1. Load authenticated user (with hash) from TinyDB.
2. `verify_password(current_password, hashed_password)` → **400** if false.
3. Reject if `new_password` equals `current_password` → **400** (optional but good UX).
4. Update `hashed_password`, return **200**.

Do **not** accept `change-password` via reset token — that flow uses `reset-password` only.

---

## 10. Email Delivery

### 10.1 Provider integration

Implement `auth/email/resend_sender.py` exposing:

```python
def send_password_reset_email(*, to_email: str, reset_link: str, expires_minutes: int) -> None:
    ...
```

Re-export from `auth/email/__init__.py` for use by the password reset service.

### 10.2 Email content requirements

| Requirement | Detail |
| --- | --- |
| Reset link | Full URL: `{PASSWORD_RESET_URL}?token={raw_token}` |
| Mobile-readable | HTML body with readable font size; include a plain-text alternative |
| Subject | Clear, e.g. `HealthCore — reset your password` |
| Expiry | State link expires in N minutes (match `RESET_TOKEN_EXPIRE_MINUTES`) |
| No secrets in logs | Do not log raw token or full reset link |

### 10.3 Development notes

Create a free [Resend](https://resend.com/) account, copy the API key, and use the onboarding sender (e.g. `onboarding@resend.dev`) during development.

---

## 11. Service Layer

### 11.1 `auth/services/password_reset.py`

Suggested responsibilities:

| Function | Purpose |
| --- | --- |
| `request_password_reset(email: str) -> None` | User lookup, token creation, email send (swallow enumeration) |
| `reset_password(token: str, new_password: str) -> None` | Validate token, update password, mark used |
| `create_reset_token(user_id: int) -> str` | Returns **raw** token for email; persists hash |
| `find_valid_token(raw_token: str) -> PasswordResetToken \| None` | Hash lookup + expiry + used check |

Keep route handlers thin — no business logic in `routes/auth.py` beyond HTTP mapping.

### 11.2 User password update

Prefer a dedicated helper in `users.py`:

```python
def update_password(user_id: int, new_password: str) -> None:
    ...
```

Reuse from both `reset-password` and `change-password` paths.

---

## 12. Error Handling Summary

| Endpoint | Condition | Status | Detail |
| --- | --- | --- | --- |
| `forgot-password` | Any input | **200** | Generic message always |
| `reset-password` | Invalid / expired / used token | **400** | Generic — e.g. `"Invalid or expired reset token."` |
| `reset-password` | Validation (password too short) | **422** | Pydantic validation |
| `reset-password` | Success | **200** | Success message |
| `change-password` | No bearer / bad JWT | **401** | Existing auth dependency |
| `change-password` | Wrong current password | **400** | `"Current password is incorrect."` |
| `change-password` | Success | **200** | Success message |

---

## 13. Public Routes (updated)

After this milestone, these auth routes remain **public** (no bearer required):

| Method | Path |
| --- | --- |
| `POST` | `/auth/login` |
| `POST` | `/auth/forgot-password` |
| `POST` | `/auth/reset-password` |
| `POST` | `/users` |

All other application data routes remain protected per M7.

---

## 14. Manual Verification

Run API with `.env` configured (`JWT_SECRET`, `PASSWORD_RESET_URL`, email provider keys).

| Step | Expected |
| --- | --- |
| `POST /auth/forgot-password` with registered email | **200** + generic message; email received with reset link |
| `POST /auth/forgot-password` with unknown email | **200** + **identical** message; no email |
| Open link token in `POST /auth/reset-password` with new password | **200**; login works with new password |
| Repeat `reset-password` with same token | **400** |
| Wait until expiry (or shorten env for test), reset again | **400** |
| Login → `POST /auth/change-password` with wrong current | **400** |
| Login → `POST /auth/change-password` with correct current + new | **200**; login works with new password |
| `POST /auth/change-password` without bearer | **401** |

Example:

```bash
BASE=http://127.0.0.1:8000

curl -s -X POST "$BASE/auth/forgot-password" \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@example.com"}'

curl -s -X POST "$BASE/auth/reset-password" \
  -H 'Content-Type: application/json' \
  -d '{"token":"<from-email>","new_password":"newsecurepass123"}'
```

---

## 15. Acceptance Checklist

### Endpoints

- [ ] `POST /auth/forgot-password` — accepts `{ email }`; **always 200**; sends email only when user exists and is active
- [ ] `POST /auth/reset-password` — accepts `{ token, new_password }`; validates signature/expiry/use; updates password; **400** for invalid, expired, or already-used tokens
- [ ] `POST /auth/change-password` — accepts `{ current_password, new_password }`; requires bearer token; **400** if current password wrong

### Reset tokens

- [ ] Tokens expire within **15–60 minutes** (configurable via env)
- [ ] Tokens invalidated after successful use — **cannot be used twice**
- [ ] Raw token never stored in DB or logs — hash only

### Email

- [ ] Integrated **Resend** for transactional email
- [ ] Email includes reset link and is readable on mobile (HTML + plain text)
- [ ] API key and sender address loaded from environment variables only

### Security

- [ ] `/forgot-password` never reveals whether an email is registered
- [ ] No API keys, secrets, or raw reset tokens in source code
- [ ] Reset and change flows use bcrypt hashing via existing security helpers

### Documentation

- [ ] New env vars documented in `services/api/.env.example`
- [ ] Email provider setup documented in `services/api/README.md`

---

## 16. Hard Constraints

| Rule | Detail |
| --- | --- |
| No enumeration | `forgot-password` → **200** always; identical response body |
| Single-use tokens | Mark `used_at` on successful reset; reject reuse with **400** |
| Short-lived tokens | **15–60 minute** expiry; enforce server-side |
| Env-only secrets | Email API keys, `JWT_SECRET`, sender addresses — never hardcoded |
| TinyDB only | Reset token rows in same auth TinyDB file — no new database engine |
| Stateless access JWT | Reset tokens are separate from access tokens — do not reuse login JWT for reset |
| Fail closed | Invalid reset token → no password change |

---

## 17. Out of Scope

- Frontend pages (`/forgot-password`, `/reset-password`, `/account/change-password`) — `specs/09_SPECS_FRONT.md`
- BFF proxy routes in Next.js apps
- Password strength meter, breach checking, or MFA
- Admin-initiated password reset
- Rate limiting / CAPTCHA (optional future hardening)
- Custom domain DNS setup for email (use provider dev/onboarding senders)
