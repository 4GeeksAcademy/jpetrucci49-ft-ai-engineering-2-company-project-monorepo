# SPECS — Milestone 8 (AUTH-02): Frontend Authentication Flows

Implementation specification for **login, registration, profile management, and route protection** in internal Next.js apps. The FastAPI service (M7) already requires JWT on protected routes — this milestone makes the UI honour that contract.

**Prerequisite:** M7 complete (`specs/07_SPECS.md`).  
**Out of scope:** `uis/website/` (M1) stays fully public. No separate auth app.

---

## 1. Objective

Integrate auth into existing monorepo apps so internal users can register, log in, manage their profile, and access protected views. Tokens live in **`localStorage`**; every protected API call sends `Authorization: Bearer <token>`.

| App | Port | Auth required |
| --- | --- | --- |
| `uis/backoffice/` | 3001 | **Yes** — all routes except `/login`, `/register` |
| `uis/talent-pipeline-tracker/` | 3002 | **Yes** — same |
| `uis/website/` | 3000 | **No** — unchanged |

---

## 2. Required Reading

| File | Use |
| --- | --- |
| `specs/07_SPECS.md` | API auth endpoints and token shape |
| `uis/backoffice/lib/api/suppliers-server.ts` | Existing BFF proxy pattern |
| `uis/backoffice/app/api/suppliers/route.ts` | Route handler to extend with `Authorization` forwarding |
| `packages/shared/navigation/` | Cross-app nav — add logout link when authenticated |
| `AGENTS.md` | Pre-commit workflow |

---

## 3. Architecture

### 3.1 Same-origin BFF (keep existing pattern)

Browser → `/api/*` on the Next.js origin → server route handler → FastAPI `:8000`.

**M7 gap to close:** BFF handlers currently omit the bearer token. Every proxy to a protected FastAPI route must forward the incoming `Authorization` header unchanged.

Public auth proxies (no token required):

| BFF route | FastAPI target |
| --- | --- |
| `POST /api/auth/login` | `POST /auth/login` |
| `POST /api/users` | `POST /users` |

Protected auth proxies (forward `Authorization`):

| BFF route | FastAPI target |
| --- | --- |
| `GET /api/auth/me` | `GET /auth/me` |
| `PUT /api/profiles/me` | `PUT /profiles/me` |

Update existing incident and supplier BFF routes the same way.

Do **not** expose FastAPI via `NEXT_PUBLIC_*` or call `:8000` from the browser.

### 3.2 Shared client auth module

Add reusable helpers under `packages/shared/auth/` (import via path alias in each app):

| Export | Responsibility |
| --- | --- |
| `TOKEN_STORAGE_KEY` | Single constant, e.g. `healthcore_access_token` |
| `getToken()` / `setToken()` / `clearToken()` | `localStorage` read/write/remove |
| `authFetch(input, init?)` | Attach bearer header; on **401** → `clearToken()` + redirect to `/login` |
| `isAuthenticated()` | `Boolean(getToken())` for guards |

No external auth libraries. React hooks only.

### 3.3 Route protection (client-side)

`localStorage` is unavailable in Next.js middleware. Protect views with a **client layout guard** (or equivalent hook), not middleware alone.

```text
app/
  (public)/
    login/page.tsx
    register/page.tsx
  (authenticated)/
    layout.tsx          ← AuthGuard: no token → redirect /login
    page.tsx            ← dashboard / home
    account/profile/page.tsx
    suppliers/ …
    incidents/ …
```

`AuthGuard` runs on mount, checks `getToken()`, redirects to `/login?next=<pathname>` if absent. Public layout has no guard.

**Website:** no auth files, no guards, no token checks.

---

## 4. Views

Implement in **both** internal apps (`backoffice`, `talent-pipeline-tracker`). Shared form components optional; behaviour must match.

### 4.1 `/login`

- Fields: `email`, `password`
- Submit → `POST /api/auth/login` (BFF sends OAuth2 form: `username=<email>&password=<password>`)
- Success → `setToken(access_token)`, redirect to `next` query param or app home (`/`)
- Failure → show API error message (generic on 401 — do not reveal whether email exists)

### 4.2 `/register`

- Fields: `email`, `password`, optional `name`, `phone`, `address`
- Submit → `POST /api/users` (JSON) → on 201, `POST /api/auth/login` with same credentials → `setToken`, redirect to `/`
- Failure → field-level or summary errors from API `detail` (422 validation, duplicate email, etc.)

### 4.3 `/account/profile`

- Load → `GET /api/auth/me` via `authFetch` → display `email`, `role`, profile `name` / `phone` / `address`
- Edit → `PUT /api/profiles/me` with changed fields only
- Success → refresh displayed data; show confirmation
- Email is read-only on this page (credential changes are out of scope unless added later)

### 4.4 Logout

- Control in app shell/header (both internal apps)
- `clearToken()` → redirect to `/login`

---

## 5. Token lifecycle

| Event | Action |
| --- | --- |
| Login / register success | `setToken(access_token)` in `localStorage` |
| Protected API call | `authFetch` adds `Authorization: Bearer <token>` |
| Logout | `clearToken()`, redirect `/login` |
| API returns **401** | `clearToken()`, redirect `/login` |
| Register | Token stored only after successful login step |

Never store passwords in `localStorage`. Never log the token.

---

## 6. Protected views inventory

### Backoffice (`uis/backoffice/`)

| Route | Protected |
| --- | --- |
| `/login`, `/register` | No |
| `/`, `/utilities`, `/incidents`, `/suppliers`, `/account/profile` | **Yes** |

Update `lib/api/incidents.ts` and `lib/api/suppliers.ts` to use `authFetch` instead of bare `fetch`.

### Talent pipeline tracker (`uis/talent-pipeline-tracker/`)

| Route | Protected |
| --- | --- |
| `/login`, `/register` | No |
| `/`, `/candidates/[id]`, `/account/profile` | **Yes** |

Add minimal BFF auth routes if this app will call the API directly; otherwise implement views + guards now so the auth shell is ready when API integration lands.

### Website (`uis/website/`)

All routes — **no changes**.

---

## 7. Project layout (target)

```text
packages/shared/auth/
  index.ts              ← token helpers + authFetch

uis/backoffice/
  app/(public)/login|register/
  app/(authenticated)/layout.tsx    ← AuthGuard
  app/(authenticated)/account/profile/
  app/api/auth/login/route.ts
  app/api/auth/me/route.ts
  app/api/users/route.ts
  app/api/profiles/me/route.ts
  lib/api/auth.ts                   ← client calls to /api/auth/*
  components/auth/                  ← LoginForm, RegisterForm, ProfileForm (optional split)

uis/talent-pipeline-tracker/
  (mirror auth routes + guards — same paths)
```

Extend `*-server.ts` proxy helpers with optional `authorization` header passthrough for incidents/suppliers.

---

## 8. Environment

No new secrets. Reuse existing BFF targets (`INCIDENTS_API_URL`, `SUPPLIERS_API_URL`). Auth proxies use the same FastAPI origin (`http://127.0.0.1:8000`).

Document any new env vars in each app's `.env.example` only if introduced.

---

## 9. Manual verification

Run `npm run dev` with API up and `JWT_SECRET` set.

| Step | Expected |
| --- | --- |
| Visit backoffice `/suppliers` logged out | Redirect to `/login` |
| Register at `/register` | 201 → auto-login → land on `/` with token in `localStorage` |
| Visit `/account/profile` | Shows email + profile from `GET /auth/me` |
| Edit profile | `PUT /profiles/me` succeeds; UI updates |
| `/suppliers` while logged in | List loads (200 via BFF with bearer) |
| Logout | Token cleared; `/suppliers` redirects to `/login` |
| Clear token manually, call protected page | Redirect `/login` |
| Expired/invalid token + API call | 401 → token cleared → `/login` |
| Visit `localhost:3000` (website) | No login prompt, no redirect |
| Talent tracker `/` logged out | Redirect `/login` |

Repeat smoke test on port 3002.

---

## 10. Acceptance checklist

### Authentication views

- [ ] `/login` — form, token stored, redirect on success, error on failure
- [ ] `/register` — `POST /users` then login, token stored, redirect; validation errors shown

### Account management

- [ ] `/account/profile` — read from `GET /auth/me`, edit via `PUT /profiles/me`

### Route protection

- [ ] All internal-app views protected except `/login` and `/register`
- [ ] Client guard redirects unauthenticated users to `/login`
- [ ] `uis/website/` entirely unaffected

### Token lifecycle

- [ ] Token in `localStorage` on login/register
- [ ] Bearer header on every protected API call (via `authFetch` + BFF forward)
- [ ] Logout clears token and redirects
- [ ] 401 clears token and redirects

### BFF

- [ ] Auth proxy routes added
- [ ] Existing incident/supplier proxies forward `Authorization`

---

## 11. Hard constraints

| Rule | Detail |
| --- | --- |
| Storage | `localStorage` only — no cookies, no session store |
| Transport | `Authorization: Bearer` header only |
| No auth app | Flows live inside existing `uis/*` apps |
| Website exempt | M1 public site must not check tokens |
| Fail closed | Missing/invalid token → no protected view access |
| BFF | Browser never calls FastAPI `:8000` directly |

---

## 12. Out of scope

- Refresh tokens, password reset, MFA, OAuth providers
- Admin user management UI
- Role-based UI hiding (optional future hardening)
- Moving token storage to httpOnly cookies
