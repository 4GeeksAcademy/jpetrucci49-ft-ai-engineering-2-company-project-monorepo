# SPECS — Milestone 6 (Step 4): Supplier Directory Frontend

Implementation specification for the HealthCore supplier directory UI in the operations backoffice. Build exactly what is described below.

This is **step 4 of 4** for the Supplier Directory. Steps 1–3 (`models.py`, seeder, `/suppliers` API) are complete and data is seeded.

---

## 1. Objective

Build a **Next.js client page** at `/suppliers` where operations staff can browse, filter, register, and manage suppliers. The UI consumes the Step 3 REST API and reflects changes immediately after each successful mutation — no full page reload.

---

## 2. Required Reading

| File | Use |
| --- | --- |
| `context/06_CONTEXT.md` | Fields to display, filter dimensions, UX expectations |
| `specs/06_SPECS_DATA.md` | Supplier field names and validation rules |
| `specs/06_SPECS_ENDPOINTS.md` | HTTP contract (`POST`, `GET`, `PATCH` endpoints) |
| `uis/backoffice/app/incidents/` | Reference for BFF proxy pattern and error handling |

---

## 3. Project Layout

```text
uis/backoffice/
  app/
    suppliers/
      page.tsx                    ← route entry
    api/
      suppliers/
        route.ts                  ← GET list, POST create (BFF proxy)
        [id]/
          route.ts                ← GET one (optional if list-only UI)
          rate/
            route.ts              ← PATCH rate
          status/
            route.ts              ← PATCH status
  components/
    suppliers/
      SupplierDirectoryPage.tsx   ← main client page
      SupplierTable.tsx           ← list + row actions
      SupplierFilters.tsx         ← country / category controls
      SupplierRegistrationForm.tsx
  lib/
    api/
      suppliers.ts                ← browser fetch helpers (same-origin)
      suppliers-server.ts         ← server proxy to FastAPI
  types/
    suppliers.ts                  ← TypeScript types matching API JSON
  components/layout/
    BackofficeShell.tsx           ← add nav link
```

Follow the **same-origin BFF pattern** used for incidents: the browser calls `/api/suppliers/*` on the backoffice origin; Next.js route handlers proxy to FastAPI at `{SUPPLIERS_API_URL}/suppliers/*` (default `http://127.0.0.1:8000`). Do **not** expose the FastAPI port via `NEXT_PUBLIC_*`.

---

## 4. Stack & Constraints

| Item | Value |
| --- | --- |
| App path | `uis/backoffice/` |
| Route | `/suppliers` |
| Framework | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4 |
| State | React hooks only — no external state libraries |
| API access | Same-origin `/api/suppliers/*` via BFF route handlers |

Add to `uis/backoffice/.env.example`:

```bash
# Server-side proxy target for supplier API (FastAPI). Not exposed to the browser.
SUPPLIERS_API_URL=http://127.0.0.1:8000
```

Reuse existing `INCIDENTS_API_URL` only if you centralise on one env var — otherwise add `SUPPLIERS_API_URL` as shown. Document in `uis/backoffice/README.md`.

**Prerequisites:** `npm run dev:api` (or `uv run uvicorn app.main:app --port 8000`) and `uv run seed` must succeed before manual testing.

---

## 5. Navigation

Add **Suppliers** to `BackofficeShell` navigation (alongside Dashboard, Incidents, Utilities):

| Link | Route |
| --- | --- |
| Suppliers | `/suppliers` |

Page heading example: **Supplier Directory**.

---

## 6. API Integration (Browser)

Client helpers in `lib/api/suppliers.ts` call same-origin BFF routes:

| UI action | BFF route | Upstream |
| --- | --- | --- |
| Load list | `GET /api/suppliers?country=&category=` | `GET /suppliers` |
| Register | `POST /api/suppliers` | `POST /suppliers` |
| Update rate | `PATCH /api/suppliers/{id}/rate` | `PATCH /suppliers/{id}/rate` |
| Change status | `PATCH /api/suppliers/{id}/status` | `PATCH /suppliers/{id}/status` |

Parse FastAPI error bodies (`detail` string or validation array) and surface a readable message in the UI — same approach as `lib/api/incidents.ts`.

Define a `SuppliersApiError` (or equivalent) in `types/suppliers.ts`.

---

## 7. Page Behaviour

Implement as a **client component** tree (`"use client"` where needed). Every async operation must show **loading** and **error** states — never fail silently.

### 7.1 Supplier list

On mount, fetch all suppliers (`GET /api/suppliers` with no filters).

Display in a **table** (preferred) or list. Minimum columns:

| Column | Source field | Notes |
| --- | --- | --- |
| Name | `name` | |
| Country | `country` | `USA` or `UK` |
| Categories | `categories` | Comma-separated or chips |
| Monthly rate | `monthly_rate` + `currency` | e.g. `4,200 USD` |
| Compliance | `compliance_agreement` | Show `BAA`, `DPA`, `both`, or `—` when null |
| Status | `status` | Badge (see §7.5) |
| Actions | — | Rate edit + status control (§7.4) |

Optional columns (`contract_renewal_date`, `contact_email`, `notes`) may be omitted or shown in an expandable row — not required for a passing submission.

Show an empty state when the filtered list has zero rows.

### 7.2 Filters (no full page reload)

Provide filter controls above the table:

| Control | Values | Behaviour |
| --- | --- | --- |
| Country | All, `USA`, `UK` | Re-fetch via `GET /api/suppliers?country=…` |
| Category | All + each `VALID_CATEGORIES` slug | Re-fetch via `GET /api/suppliers?category=…` |

- Changing a filter updates the list **in place** (client state + API call) — do not navigate away or reload the document.
- When both filters are set, pass both query parameters (API applies AND).
- **All** clears that query parameter.

Use human-readable labels for category slugs in the dropdown (e.g. `medical_supplies` → "Medical supplies").

Valid category slugs match `VALID_CATEGORIES` in `services/api/models.py`.

### 7.3 Register new supplier

Provide a form (section above the table or modal) with fields matching `SupplierCreate`:

| Field | Required |
| --- | --- |
| `name` | ✅ |
| `country` | ✅ (`USA` / `UK`) |
| `categories` | ✅ (multi-select; at least one) |
| `monthly_rate` | ✅ |
| `currency` | ✅ (auto-suggest or lock based on country) |
| `status` | ✅ (`active` / `suspended`) |
| `compliance_agreement` | Optional |
| `contract_renewal_date` | Optional |
| `contact_email` | Optional |
| `notes` | Optional |

On submit:

1. `POST /api/suppliers` with JSON body.
2. On **201**, prepend or merge the returned supplier into the list immediately.
3. On **422** or other error, show the API error message — do not clear the form unless submission succeeded.
4. Show loading state on the submit button while in flight.

Enforce country–currency pairing in the form UX (e.g. selecting `USA` sets currency to `USD`) to reduce avoidable 422 responses.

### 7.4 Row actions

Each row must support:

**Update rate**

- Inline input or small edit control for `monthly_rate`.
- On save, `PATCH /api/suppliers/{id}/rate` with `{ "monthly_rate": <number> }`.
- On success, update that row in local state (including `updated_at` from the response).
- Reject zero/negative values in the UI before calling the API when practical; still handle 422 from the API.

**Activate / suspend**

- Visible control per row (toggle, button, or select) for `active` ↔ `suspended`.
- `PATCH /api/suppliers/{id}/status` with `{ "status": "active" | "suspended" }`.
- On success, update the row's `status` in local state immediately.

Show per-row or inline error text if a PATCH fails.

### 7.5 Status styling

Visually distinguish **active** vs **suspended** suppliers:

| Status | Treatment |
| --- | --- |
| `active` | Green or neutral positive badge (e.g. "Active") |
| `suspended` | Muted/warning badge (e.g. amber "Suspended") |

Apply badge styling in the status column. Optionally de-emphasise suspended rows (lighter text or background) — badge alone is sufficient for acceptance.

---

## 8. TypeScript Types

`types/suppliers.ts` must mirror the API `Supplier` JSON shape:

```typescript
interface Supplier {
  id: number;
  name: string;
  country: "USA" | "UK";
  categories: string[];
  monthly_rate: number;
  currency: "USD" | "GBP";
  status: "active" | "suspended";
  compliance_agreement: "BAA" | "DPA" | "both" | null;
  contract_renewal_date: string | null;
  contact_email: string | null;
  notes: string | null;
  updated_at: string;
}
```

Request payloads for create/rate/status may reuse narrower types aligned with the API models.

---

## 9. Manual Verification

1. Start API and seed data; start backoffice (`npm run dev` or `npm run dev:backoffice`).
2. Open http://localhost:3001/suppliers — seeded suppliers appear.
3. Filter by **USA** — only USA suppliers shown; no page reload.
4. Filter by **clinical_software** — matching rows only.
5. Register a new supplier — appears in the list on success; invalid input shows an error.
6. Change a row's rate — list updates with new rate after save.
7. Suspend a supplier — badge changes to suspended styling.
8. Network tab shows requests to `/api/suppliers/*`, not direct `:8000` calls from the browser.

---

## 10. Acceptance Checklist

- [ ] Create a supplier directory page accessible from the application menu.
- [ ] Display the full list of suppliers in a table or list with their main fields from the CONTEXT, and status.
- [ ] Include filter controls by country and by category that update the list without reloading the page.
- [ ] Implement a form to register a new supplier that consumes the `POST /suppliers` endpoint. Display an error message if the API rejects the input.
- [ ] Allow updating the rate field defined in the CONTEXT from the interface and reflect the change in the list immediately after the API responds.
- [ ] Allow changing a supplier's status (activate / suspend) from the interface with a visible control on each row or in the detail view.
- [ ] Visually distinguish active suppliers from suspended ones (for example, with a colour-coded badge or differentiated style).
- [ ] BFF route handlers proxy to FastAPI; `SUPPLIERS_API_URL` documented in `.env.example`
- [ ] Loading and error states for list load, create, rate update, and status change

---

## 11. Out of Scope

- `DELETE /suppliers/{id}` from the UI (API supports it; not required for this page)
- Dedicated supplier detail route (`/suppliers/[id]`) unless needed for row actions
- Authentication or role-based access
- Edit of fields other than rate and status (no general edit form)
