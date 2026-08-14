# SPECS — Milestone 9 (AUTH-03): Password Recovery and Change — Frontend

Implementation specification for **forgot password, reset password, and change password** in internal Next.js apps.

**Prerequisite:** `specs/09_SPECS_BACK.md` complete (API endpoints live).  
**Out of scope:** `uis/website/` — unchanged.

---

## 1. Scope

| App | Port | New routes |
| --- | --- | --- |
| `uis/backoffice/` | 3001 | `/forgot-password`, `/reset-password`, `/account/change-password` |
| `uis/talent-pipeline-tracker/` | 3002 | Same paths and behaviour |

Both apps already have M8 auth (`/login`, `/register`, `AuthGuard`, BFF auth routes). Extend that pattern — do not introduce a new auth stack.

---

## 2. BFF routes

Browser → same-origin `/api/*` → FastAPI `:8000`. No direct `:8000` calls from the client.

| BFF route | FastAPI target | Auth |
| --- | --- | --- |
| `POST /api/auth/forgot-password` | `POST /auth/forgot-password` | Public |
| `POST /api/auth/reset-password` | `POST /auth/reset-password` | Public |
| `POST /api/auth/change-password` | `POST /auth/change-password` | Forward `Authorization` |

Mirror existing handlers in `app/api/auth/login/route.ts` and `app/api/auth/me/route.ts`. Reuse `getFastApiOrigin()` and `forwardAuthorization()` from `@healthcore/api/proxy`.

Set `PASSWORD_RESET_URL` in `services/api/.env` to the app you test first (e.g. `http://localhost:3001/reset-password`). Email links must land on a page that exists in that app.

---

## 3. Route groups

```text
app/
  (public)/
    login/page.tsx              ← add "Forgot your password?" link
    forgot-password/page.tsx
    reset-password/page.tsx
  (authenticated)/
    account/profile/page.tsx
    account/change-password/page.tsx
```

| Route | Guard |
| --- | --- |
| `/forgot-password`, `/reset-password` | Public — no `AuthGuard` |
| `/account/change-password` | Protected — inside `(authenticated)/` |

Update `(public)` route lists in docs/comments if present; no middleware changes required.

---

## 4. Views

Implement in **both** internal apps. Per-app components under `components/auth/` (same approach as M8 login/register forms).

### 4.1 `/login` (update)

Add a **"Forgot your password?"** link to `/forgot-password`.

### 4.2 `/forgot-password`

- Single field: `email`
- Submit → `POST /api/auth/forgot-password` with `{ email }`
- **Always** show confirmation after submit: *"If that address is registered, you'll receive a link shortly."* (match API message)
- **Disable** the form after successful submit to prevent duplicate requests
- Do not reveal whether the email exists (API always returns 200)

### 4.3 `/reset-password`

- Read `token` from URL query string (`useSearchParams`)
- Fields: `new_password`, `confirm_password`
- Client-side: reject submit if passwords do not match (show error before calling API)
- Submit → `POST /api/auth/reset-password` with `{ token, new_password }`
- **Success** → redirect to `/login?message=...` (or equivalent) with a visible success banner
- **Failure** (400 — invalid/expired/used token) → clear error + link to `/forgot-password`
- If `token` query param is missing, show error and link to `/forgot-password` (no API call)

### 4.4 `/account/change-password`

- Fields: `current_password`, `new_password`, `confirm_password`
- Client-side: reject if `new_password !== confirm_password`
- Submit → `POST /api/auth/change-password` via `authFetch` (bearer attached)
- **Success** → confirmation message; optional redirect to `/account/profile`
- **400** wrong current password → show API `detail`
- Add nav link from account area (e.g. profile page or shell) to this route

---

## 5. Client API helpers

Add thin fetch wrappers in each app's `lib/api/auth.ts` (or extend existing file):

| Function | Calls |
| --- | --- |
| `forgotPassword(email)` | `POST /api/auth/forgot-password` |
| `resetPassword(token, newPassword)` | `POST /api/auth/reset-password` |
| `changePassword(currentPassword, newPassword)` | `POST /api/auth/change-password` via `authFetch` |

Reuse `parseApiError` from `@healthcore/auth` for error display.

---

## 6. Security (frontend)

| Rule | Implementation |
| --- | --- |
| No enumeration | Forgot-password UI never implies whether email exists |
| Reset token in URL only | Pass `token` from query to API body; do not store in `localStorage` |
| Change password | Requires session; use `authFetch` only |
| Password min length | Enforce 8+ chars in forms (match API) |

---

## 7. Manual verification

With API running and Resend configured:

| Step | Expected |
| --- | --- |
| `/login` shows forgot-password link | Link navigates to `/forgot-password` |
| Submit forgot-password (known email) | Confirmation shown; form disabled; email received |
| Submit forgot-password (unknown email) | Same confirmation; form disabled |
| Open reset link from email | `/reset-password?token=...` loads form |
| Submit matching new passwords | Redirect to `/login` with success message |
| Submit reset again with same token | Error + link to `/forgot-password` |
| `/account/change-password` while logged out | Redirect to `/login` |
| Change password with wrong current | Error shown |
| Change password with correct current | Success; login works with new password |
| Repeat on port 3002 | Same behaviour |
| Visit `localhost:3000` | No new auth routes or prompts |

---

## 8. Acceptance checklist

- [ ] BFF: `forgot-password`, `reset-password`, `change-password` proxies added (both apps)
- [ ] `/forgot-password` — confirmation message, form disabled after submit
- [ ] `/reset-password` — token from query, confirmation match, success → `/login`, failure → error + forgot link
- [ ] `/account/change-password` — current + new + confirm, `authFetch`, validation before API
- [ ] `/login` — "Forgot your password?" link
- [ ] `uis/website/` untouched

---

## 9. Out of scope

- Password strength meter, MFA, admin-initiated reset
- Role-based hiding of change-password link
- Shared React forms in `packages/shared/` (optional; per-app `components/auth/` is fine)
