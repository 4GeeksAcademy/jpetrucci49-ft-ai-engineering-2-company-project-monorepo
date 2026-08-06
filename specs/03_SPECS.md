# SPECS — Milestone 3: Talent Pipeline Tracker

Implementation specification for the HealthCore candidate management frontend. Build exactly what is described below.

---

## 1. Objective

Build a **Next.js frontend** for HealthCore's People & Talent team to manage an active recruitment pipeline. The backend REST API already exists — implement the UI only.

The team is replacing a shared spreadsheet with 100+ applications. The tool must be reliable: show loading and error states for every async operation; never fail silently.

---

## 2. Project Location & Stack

| Item | Value |
| --- | --- |
| App path | `uis/talent-pipeline-tracker/` |
| Framework | Next.js (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS v4 |
| API base URL env var | `NEXT_PUBLIC_API_URL` |
| API base URL value | `https://playground.4geeks.com/tracker/api/v1` |
| API docs | https://playground.4geeks.com/tracker/api/v1/docs |

**Constraints**

- Use only Next.js, React, and TypeScript.
- Do **not** use external state libraries (Redux, Zustand, Jotai, etc.). Component-level hooks only.
- Commit `.env.example` with `NEXT_PUBLIC_API_URL`. Do **not** commit `.env.local`.
- UI labels and framing must reflect **HealthCore** / People & Talent context. API field names stay as defined by the backend.

---

## 3. Routes

| Route | Purpose |
| --- | --- |
| `/` | Candidate list |
| `/candidates/[id]` | Candidate detail |

Use Next.js client-side navigation between list and detail — no full page reloads.

---

## 4. API Contract

All requests use `NEXT_PUBLIC_API_URL` as the base. Handle with `async/await`.

### 4.1 Records

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/records` | List candidates |
| `POST` | `/records` | Register candidate |
| `GET` | `/records/:id` | Get candidate by ID |
| `PUT` | `/records/:id` | Replace candidate data |
| `PATCH` | `/records/:id` | Update status and/or stage |

**`GET /records` query parameters**

| Param | Type | Description |
| --- | --- | --- |
| `status` | string | Filter: `received`, `in_progress`, `selected`, `discarded` |
| `stage` | string | Filter: `pending`, `review`, `personal_interview`, `technical_interview`, `offer_presented` |
| `search` | string | Search in `full_name` or `email` |
| `page` | integer | Page number (default 1) |
| `limit` | integer | Results per page (default 20) |

**`RecordOut`** (response shape)

```typescript
interface RecordOut {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  status: string;
  stage: string;
  experience_years: number;
  notes_count: number;
  applied_at: string;
  updated_at: string;
}
```

**`RecordCreate`** (POST and PUT body)

```typescript
interface RecordCreate {
  full_name: string;       // required
  email: string;           // required, email format
  phone: string;           // required
  position: string;        // required
  experience_years: number; // required
  linkedin_url?: string | null;
  cv_url?: string | null;
}
```

**`RecordPatch`** (PATCH body — send only fields being changed)

```typescript
interface RecordPatch {
  status?: string | null;
  stage?: string | null;
}
```

### 4.2 Notes

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/records/:id/notes` | List notes for a candidate |
| `POST` | `/records/:id/notes` | Add note |
| `DELETE` | `/records/:id/notes/:note_id` | Delete note |

**`NoteCreate`** (POST body)

```typescript
interface NoteCreate {
  content: string; // required, min length 1
}
```

---

## 5. UI Label Mappings

**Never display raw API values** for `status` or `stage`. Always use these labels:

### Status

| API value | UI label |
| --- | --- |
| `received` | Received |
| `in_progress` | In progress |
| `selected` | Selected |
| `discarded` | Discarded |

### Stage

| API value | UI label |
| --- | --- |
| `pending` | Pending review |
| `review` | Under review |
| `personal_interview` | Personal interview |
| `technical_interview` | Technical interview |
| `offer_presented` | Offer presented |

---

## 6. Features

### 6.1 Candidate list (`/`)

- Fetch candidates from `GET /records`.
- Display per row: **full name**, **position**, **status** (label), **stage** (label).
- **Filter by status** and **filter by stage** using URL query parameters via `useSearchParams`.
- **Search by name or email** without full page reload (client-side or via API `search` param).
- Link each row to `/candidates/[id]`.
- Show **loading** while fetching; show **error** message on failure.
- Include UI to **register a new candidate** (`POST /records`).

### 6.2 Candidate detail (`/candidates/[id]`)

- Fetch candidate from `GET /records/:id`.
- Display all fields: name, email, phone, position, LinkedIn, CV link, years of experience, status (label), stage (label), application date.
- **Update status or stage** via `PATCH /records/:id` (single interaction control).
- **Notes section** (detail view only):
  - List notes from `GET /records/:id/notes`
  - Add note via `POST /records/:id/notes`
  - Delete note via `DELETE /records/:id/notes/:note_id`
- **Edit candidate** form via `PUT /records/:id` with all `RecordCreate` fields.
- Validate required fields before submit; show **success** and **error** feedback after mutations.

### 6.3 Async & state behaviour

- Every data fetch and mutation: **loading**, **success**, and **error** UI states.
- After `PATCH`, `PUT`, or `POST`, refresh or update local state so the UI reflects changes **without a full page reload**.
- No prop drilling — keep state scoped appropriately per component.

---

## 7. Code Structure

Organize under `uis/talent-pipeline-tracker/`:

```text
uis/talent-pipeline-tracker/
├── app/                  # Next.js App Router pages
├── components/           # UI components
├── types/                # TypeScript types (RecordOut, RecordCreate, etc.)
├── lib/ or services/     # API client / fetch helpers
└── hooks/                # Optional custom hooks
```

- Define TypeScript types for all API request/response shapes.
- Separate data-access logic from presentation components.

---

## 8. Acceptance Criteria

- [ ] List page renders candidates from `GET /records` with name, position, status label, stage label
- [ ] Status and stage filters work via query parameters without full page reload
- [ ] Search by name or email works without full page reload
- [ ] Detail page loads correct candidate by ID and shows all required fields
- [ ] Status and stage updatable from detail view via `PATCH`
- [ ] Notes listable, addable, and deletable from detail view only
- [ ] New candidate registrable via `POST` with all required API fields validated
- [ ] Candidate editable via `PUT` with validation and feedback
- [ ] Loading, success, and error states visible for all async operations
- [ ] TypeScript types defined and used for API data
- [ ] Components, types, and API logic in separate folders
- [ ] Next.js App Router used for navigation and dynamic routes
- [ ] Status/stage show human-readable labels, never raw API values
- [ ] UI framed as HealthCore People & Talent internal tool

---

## 9. Out of Scope

- Backend API changes
- External state management libraries
- Formal visual design evaluation (interface must still be usable and show all required information clearly)

---

## References

- `context/03_CONTEXT.md` — HealthCore scenario, label mappings, acceptance criteria
- `milestones/03_README.md` — milestone requirements and evaluation checklist
