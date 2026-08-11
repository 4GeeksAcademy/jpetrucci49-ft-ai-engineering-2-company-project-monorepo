# SPECS — Milestone 7 (AUTH-01): Authentication and Route Protection

Implementation specification for **stateless JWT authentication** on the HealthCore FastAPI service. Build exactly what is described below.

This is a **security milestone**, not a feature milestone. Incorrect auth is worse than no auth — validate tokens on every protected handler, hash every password, and fail closed.

**Out of scope here:** frontend token handling (backoffice BFF updates come later). Expect existing unauthenticated API calls to return **401** until the UI is updated.

---

## 1. Objective

Add credential storage, login, and a reusable `get_current_user` dependency. Protect sensitive routes so unauthenticated callers cannot read or mutate operational data.

| Module | Storage | Purpose |
| --- | --- | --- |
| `User` | TinyDB | Credentials only — `email`, `hashed_password`, `role`, flags |
| `Profile` | TinyDB | One-to-one display/contact data linked by `user_id` |

The JWT **`sub` claim (or equivalent) must be the TinyDB user `id` (int)**. Downstream modules (inventory, etc.) reference this value as `user_uuid`. Never put passwords or profile PII in the token.

---

## 2. Required Reading

| File | Use |
| --- | --- |
| `services/api/app/main.py` | Router mounting |
| `services/api/database.py` | TinyDB pattern for suppliers |
| `services/api/routes/suppliers.py` | Routes to protect |
| `services/api/app/incidents/router.py` | Routes to protect |
| `AGENTS.md` | Pre-commit workflow |

---

## 3. Project Layout

```text
services/api/
  app/
    main.py                    ← mount auth routers; no logic changes to CORS beyond existing
  auth/
    __init__.py
    models.py                    ← User, Profile, Role enum, request/response schemas
    database.py                  ← TinyDB tables: users, profiles (separate file from suppliers)
    security.py                  ← password hash/verify, JWT encode/decode
    dependencies.py              ← OAuth2PasswordBearer, get_current_user, require_admin
    services/
      users.py                   ← user CRUD + profile create on register
      profiles.py                ← profile read/update/delete-by-user
  routes/
    auth.py                      ← prefix /auth
    users.py                     ← prefix /users
    profiles.py                  ← prefix /profiles
  .env.example                   ← JWT_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES
  pyproject.toml                 ← add pyjwt, libpass[bcrypt]
```

Keep supplier and incident code unchanged except adding `Depends(get_current_user)` (or stricter deps) on protected handlers.

**Do not** create User/Profile tables in Supabase or SQLModel now or later. TinyDB only.

---

## 4. Stack and Dependencies

| Item | Value |
| --- | --- |
| Framework | FastAPI |
| Token transport | `Authorization: Bearer <token>` only — **no cookies, no server sessions** |
| Token scheme | `OAuth2PasswordBearer` (`tokenUrl="/auth/login"`) |
| JWT | **PyJWT** — algorithm **HS256** only; always pass explicit `algorithms=["HS256"]` on decode |
| Passwords | **libpass** with **bcrypt** via `CryptContext` — never store or compare plain text |
| Storage | TinyDB — default file `services/api/auth.json` (override via `AUTH_DB_PATH`) |

Add to `pyproject.toml` (do **not** install unmaintained `passlib` or `python-jose`):

```toml
"libpass[bcrypt]>=1.9,<2",
"pyjwt>=2.8,<3",
```

Implementation patterns live in §8. Follow [FastAPI OAuth2 + JWT tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) (PyJWT + password hashing).

---

## 5. Environment Variables

Document in `services/api/.env.example`:

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `JWT_SECRET` | **Yes** | — | HMAC signing key; load from env only — **never hardcode** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifetime |
| `AUTH_DB_PATH` | No | `auth.json` | TinyDB file for users + profiles |

Startup must fail fast if `JWT_SECRET` is missing in non-test environments.

---

## 6. Data Models (TinyDB)

### 6.1 `User` (credentials)

| Field | Type | Rules |
| --- | --- | --- |
| `id` | `int` | TinyDB doc id; set after insert |
| `email` | `str` | Unique, valid email format |
| `hashed_password` | `str` | Bcrypt hash only — **never returned in API responses** |
| `is_active` | `bool` | Default `true`; inactive users cannot log in |
| `role` | enum | **`admin` \| `manager` \| `user` only** — reject other values via `Enum` or validator |
| `created_at` | `str` (ISO UTC) | Server-set on create |

**Forbidden on `User`:** `name`, `phone`, `address`, or any display/contact field.

New registrations via `POST /users` default `role` to **`user`**. Only an `admin` may set or change `role` to `admin` or `manager`.

### 6.2 `Profile` (one-to-one)

| Field | Type | Rules |
| --- | --- | --- |
| `id` | `int` | TinyDB doc id |
| `user_id` | `int` | FK to `User.id` — exactly one profile per user |
| `name` | `str` | Display name |
| `phone` | `str \| null` | Optional |
| `address` | `str \| null` | Optional |

Enforce uniqueness of `user_id` in the service layer before insert.

### 6.3 API response shapes

- **`UserPublic`:** `id`, `email`, `is_active`, `role`, `created_at` — no hash.
- **`ProfilePublic`:** `id`, `user_id`, `name`, `phone`, `address`.
- **`Token`:** `{ "access_token": "<jwt>", "token_type": "bearer" }`.
- **`AuthMe`:** `email`, `role`, `profile` (`ProfilePublic`).

---

## 7. Service Layer

Implement in `auth/services/` — routes call services; services talk to TinyDB.

### 7.1 User service (`auth/services/users.py`)

| Function | Behaviour |
| --- | --- |
| `create_user(...)` | Hash password; insert user; create linked profile when optional profile fields supplied; return `(UserPublic, ProfilePublic)` |
| `get_user_by_id(id)` | Return user or `None` |
| `get_user_by_email(email)` | Return user (including hash for login) or `None` |
| `list_users()` | All users — credentials stripped |
| `update_user(id, ...)` | Update allowed fields; hash new password if provided |
| `delete_user(id)` | Remove user **and** linked profile |

### 7.2 Profile service (`auth/services/profiles.py`)

| Function | Behaviour |
| --- | --- |
| `get_profile_by_user_id(user_id)` | Return profile or `None` |
| `update_profile(user_id, ...)` | Update `name`, `phone`, `address` |
| `delete_profile_by_user_id(user_id)` | Called from `delete_user` |

---

## 8. Security (`auth/security.py`)

Centralise password and token logic here. Routes and dependencies must call these helpers — no inline hashing or JWT code.

### 8.1 Password hashing (libpass)

Install **`libpass[bcrypt]`** (maintained fork). It exposes `passlib.context` — that import path is correct; do not install the separate PyPI package named `passlib`.

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

### 8.2 JWT (PyJWT)

```python
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

ALGORITHM = "HS256"

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, JWT_SECRET, algorithm=ALGORITHM)

def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    return int(payload["sub"])
```

Raise or let `InvalidTokenError` propagate to `get_current_user`, which maps failures to **401**.

JWT payload (minimum):

```json
{ "sub": "<user_id_as_string>", "exp": <unix_timestamp> }
```

Use `ACCESS_TOKEN_EXPIRE_MINUTES` for `exp`. Sign with `JWT_SECRET`.

---

## 9. Dependencies (`auth/dependencies.py`)

### 9.1 `get_current_user`

1. Read bearer token via `OAuth2PasswordBearer(tokenUrl="/auth/login")`.
2. Decode JWT with PyJWT → `user_id`.
3. Load user from TinyDB.
4. Reject if user missing, inactive, or token invalid/expired → **`401 Unauthorized`** with `{ "detail": "..." }`.
5. Return the user model (without hash) for handlers.

### 9.2 Optional helpers

| Dependency | Use |
| --- | --- |
| `require_admin` | `role == admin` else **`403 Forbidden`** |
| `require_self_or_admin(user_id)` | Caller is target user or admin else **403** |

**401 vs 403**

| Situation | Status |
| --- | --- |
| Missing / invalid / expired token | **401** |
| Valid token but insufficient role or not owner | **403** |

---

## 10. REST Endpoints

Mount routers in `app/main.py`. Tag OpenAPI groups: `auth`, `users`, `profiles`.

### 10.1 `/auth`

| Method | Path | Auth | Body / response |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | **Public** | `{ "email", "password" }` → `Token`. Reject wrong credentials with **401** (generic message — do not reveal whether email exists). Reject inactive user with **401**. |
| `GET` | `/auth/me` | **Protected** | → `AuthMe` (`email`, `role`, linked `Profile`) |

Login uses standard OAuth2 password flow compatible with `/docs` **Authorize** button when `OAuth2PasswordRequestForm` is used, or accept JSON body if you wrap it — document the chosen shape in `routes/auth.py`.

### 10.2 `/users`

| Method | Path | Auth | Rules |
| --- | --- | --- | --- |
| `POST` | `/users` | **Public** | Register. Body: `email`, `password`, optional `name`, `phone`, `address`. Hash password; default `role=user`; create profile. → **201** `UserPublic` + profile (or combined response). |
| `GET` | `/users` | **Protected** | **`admin` only** → list `UserPublic[]` |
| `GET` | `/users/{id}` | **Protected** | **Self or admin** → `UserPublic` |
| `PUT` | `/users/{id}` | **Protected** | **Self or admin**. Self may update `email` (and password if exposed). **`role` changes: admin only**. → `UserPublic` |
| `DELETE` | `/users/{id}` | **Protected** | **Self or admin**. Delete user + profile. → **204** |

Never return `hashed_password` in any response.

### 10.3 `/profiles`

| Method | Path | Auth | Rules |
| --- | --- | --- | --- |
| `GET` | `/profiles/me` | **Protected** | Owner only → `ProfilePublic` |
| `PUT` | `/profiles/me` | **Protected** | Owner only — update `name`, `phone`, `address` → `ProfilePublic` |

No `DELETE /profiles/me` — profile is removed only when the user is deleted.

---

## 11. Route Protection (existing API)

Apply `Depends(get_current_user)` to every handler below. No anonymous access.

### 11.1 Incidents (`/api/incidents`)

| Method | Path |
| --- | --- |
| `POST` | `/api/incidents/analyze` |
| `GET` | `/api/incidents/results/export` |

### 11.2 Suppliers (`/suppliers`)

| Method | Path |
| --- | --- |
| `POST` | `/suppliers` |
| `GET` | `/suppliers` |
| `GET` | `/suppliers/{id}` |
| `PATCH` | `/suppliers/{id}/rate` |
| `PATCH` | `/suppliers/{id}/status` |
| `DELETE` | `/suppliers/{id}` |

**Public routes after this milestone (only):**

- `POST /auth/login`
- `POST /users` (registration)
- `GET /docs`, `GET /openapi.json`, `GET /` (FastAPI defaults)

Everything else that reads or mutates application data requires a valid bearer token.

### 11.3 Applying the dependency

```python
from auth.dependencies import get_current_user

@router.get("")
def list_suppliers(
    current_user: Annotated[UserPublic, Depends(get_current_user)],
    ...
):
    ...
```

Do not duplicate JWT logic inside route handlers.

---

## 12. Token Consumption

1. Register via `POST /users`, then `POST /auth/login` → copy `access_token`.
2. Send `Authorization: Bearer <access_token>` on protected routes.
3. In `/docs`: **Authorize** → paste token (or OAuth2 form if login uses `OAuth2PasswordRequestForm`).

Tokens are stateless — no session store. Expired or invalid tokens → **401**.

---

## 13. Manual Verification

Run from `services/api/` with `uv run uvicorn app.main:app --reload --port 8000`.

| Step | Expected |
| --- | --- |
| `POST /users` with email + password | **201**; user + profile created |
| `POST /auth/login` with same credentials | **200** + `access_token` |
| `GET /auth/me` with `Authorization: Bearer …` | **200** + email, role, profile |
| `GET /suppliers` **without** token | **401** |
| `GET /suppliers` **with** valid token | **200** |
| Protected route with expired or garbage token | **401** |
| `GET /users` as non-admin | **403** |
| `PUT /users/{other_id}` as non-admin non-self | **403** |

---

## 14. Acceptance Checklist

### User model and CRUD

- [ ] `User` in TinyDB: `id`, `email`, `hashed_password`, `is_active`, `role`, `created_at` — no display/contact fields on `User`
- [ ] `role` enum: `admin`, `manager`, `user` only; `POST /users` defaults to `user`
- [ ] Service layer: create, get by id, get by email, update, delete
- [ ] `POST /users` — register; hash password; optional profile fields create linked `Profile`
- [ ] `GET /users` — list (admin only, protected)
- [ ] `GET /users/{id}` — get one (self or admin, protected)
- [ ] `PUT /users/{id}` — update credentials; role change admin-only (self or admin, protected)
- [ ] `DELETE /users/{id}` — delete user + profile (self or admin, protected)

### Profile model and endpoints

- [ ] `Profile` in TinyDB: `id`, `user_id`, `name`, `phone`, `address`; one-to-one with `User`
- [ ] `GET /profiles/me` — authenticated owner's profile
- [ ] `PUT /profiles/me` — owner updates name, phone, address

### Authentication endpoints

- [ ] `POST /auth/login` — validate credentials → JWT
- [ ] `GET /auth/me` — email, role, linked profile

### Token and dependency

- [ ] `get_current_user` — bearer header, PyJWT decode, load user, **401** on any failure
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` and `JWT_SECRET` from env — secret never hardcoded
- [ ] Password hashing via **libpass** + bcrypt; JWT via **PyJWT** with explicit `algorithms=["HS256"]`

### Route protection

- [ ] All `/users` routes protected except `POST /users`
- [ ] `/auth/me` protected
- [ ] At least **5 existing non-auth routes** protected (spec lists **8** above)
- [ ] **401** unauthenticated; **403** unauthorized role/ownership

### Testing

- [ ] Full flow in `/docs`: register → login → token → protected route
- [ ] Protected route without token → **401**
- [ ] Expired or malformed token → **401**

---

## 15. Hard Constraints

| Rule | Detail |
| --- | --- |
| TinyDB only | User and Profile never in Supabase/SQLModel |
| JWT only | No session cookies, no server-side session store |
| Libraries | **PyJWT** for tokens; **libpass[bcrypt]** for passwords — not `python-jose` or `passlib` |
| Token payload | Carry TinyDB user `id` as `sub`; other modules reference it as `user_uuid` |
| Fail closed | When in doubt, require authentication |

---

## 16. Out of Scope

- Backoffice BFF sending `Authorization` headers (follow-up milestone)
- Refresh tokens, password reset email, MFA
- Role-based restrictions on supplier/incident routes beyond “authenticated” (optional future hardening)
- Seeding admin users (optional `auth/seed.py` — not required for acceptance)
