# SPECS — Milestone 6 (Step 3): Supplier Directory API Endpoints

Implementation specification for the HealthCore supplier registry **REST API**. Build exactly what is described below.

This is **step 3 of 4** for the Supplier Directory (FastAPI + TinyDB + Pydantic). Steps 1–2 (`models.py`, `database.py`, `seed.py`) are complete. Step 4 will cover the frontend.

---

## 1. Objective

Expose CRUD and lifecycle operations for suppliers over HTTP. All write payloads must pass through the Step 1 Pydantic models before touching TinyDB. Invalid input returns **`422 Unprocessable Entity`** with FastAPI validation detail — not silent coercion.

---

## 2. Required Reading

| File | Use |
| --- | --- |
| `context/06_CONTEXT.md` | Field rules, valid statuses/categories, country–currency pairing |
| `specs/06_SPECS_DATA.md` | Request/response models, `updated_at` behaviour |
| `specs/06_SPECS_SEEDER.md` | TinyDB access via `database.py` |

---

## 3. Project Layout (This Step)

```text
services/
  api/
    models.py            ← Step 1 (complete)
    database.py          ← Step 2 (complete)
    seed.py              ← Step 2 (complete)
    routes/
      suppliers.py       ← supplier router (this step)
    app/
      main.py            ← mount supplier router (this step)
uis/
  backoffice/
    app/
      suppliers/         ← frontend (Step 4)
```

Implement route handlers in `routes/suppliers.py`. Register the router in `app/main.py`. Reuse `get_suppliers_table()` from `database.py` — do not open a second TinyDB connection.

---

## 4. Stack

| Item | Value |
| --- | --- |
| Framework | FastAPI |
| Server | uvicorn (`npm run dev:api` or `uv run uvicorn app.main:app --reload --port 8000`) |
| Storage | TinyDB via `database.py` |
| Default port | `8000` |
| Route prefix | `/suppliers` |

Response bodies use the `Supplier` model from `models.py` unless noted otherwise.

---

## 5. Shared Rules

| Rule | Detail |
| --- | --- |
| Validation | `SupplierCreate`, `SupplierRateUpdate`, `SupplierStatusUpdate` for request bodies; reject invalid data with **422** |
| `updated_at` | Set by the server — never accepted from clients (see `06_SPECS_DATA.md` §8) |
| `id` | TinyDB document id (`int`); assigned on create |
| Create | Set `updated_at` to current UTC on insert |
| Rate change | Set `updated_at` to current UTC when `monthly_rate` changes |
| Status change | Do **not** change `updated_at` |
| Other field updates | Not exposed in this step (only create, list, get, rate, status, delete) |
| Not found | Missing supplier id → **404** with `{ "detail": "..." }` |
| Positive rate | `monthly_rate` must be **> 0** — enforced by Pydantic before handler logic |

---

## 6. Endpoints

### 6.1 `POST /suppliers`

Register a new supplier.

| Item | Specification |
| --- | --- |
| Request body | `SupplierCreate` |
| Success status | `201 Created` |
| Response body | `Supplier` (includes TinyDB-assigned `id` and server `updated_at`) |
| Invalid input | **422** — validation errors from Pydantic |

**Flow:**

1. Validate body with `SupplierCreate`.
2. Insert into TinyDB; assign `id` from document id.
3. Set `updated_at` to `datetime.now(timezone.utc)`.
4. Return full `Supplier`.

---

### 6.2 `GET /suppliers`

List suppliers with optional filters.

| Item | Specification |
| --- | --- |
| Success status | `200 OK` |
| Response body | `list[Supplier]` (JSON array; may be empty) |

**Query parameters**

| Param | Type | Required | Description |
| --- | --- | --- | --- |
| `country` | string | No | Filter by contract country: `USA` or `UK` |
| `category` | string | No | Filter by product/service category — return suppliers whose `categories` list **includes** this value |

- If **no** query parameters are provided, return **all** suppliers.
- If both are provided, apply **both** filters (AND).
- Invalid `country` or unknown `category` value → **422**.
- Valid `category` values are exactly those in `VALID_CATEGORIES` (`models.py`).

---

### 6.3 `GET /suppliers/{id}`

Return one supplier by id.

| Item | Specification |
| --- | --- |
| Path param | `id` — integer TinyDB document id |
| Success status | `200 OK` |
| Response body | `Supplier` |
| Not found | **404** |

---

### 6.4 `PATCH /suppliers/{id}/rate`

Update a supplier's monthly rate.

| Item | Specification |
| --- | --- |
| Request body | `SupplierRateUpdate` (`monthly_rate` only) |
| Success status | `200 OK` |
| Response body | Updated `Supplier` |
| Invalid rate (≤ 0) | **422** (Pydantic `Field(gt=0)`) |
| Not found | **404** |

**Side effects:**

1. Persist new `monthly_rate`.
2. Set `updated_at` to current UTC at the time of the change.

---

### 6.5 `PATCH /suppliers/{id}/status`

Activate or suspend a supplier.

| Item | Specification |
| --- | --- |
| Request body | `SupplierStatusUpdate` (`status` only) |
| Allowed values | `active`, `suspended` (from `SupplierStatus` enum) |
| Success status | `200 OK` |
| Response body | Updated `Supplier` |
| Invalid status | **422** |
| Not found | **404** |

Do **not** modify `updated_at` on status-only changes.

---

### 6.6 `DELETE /suppliers/{id}`

Remove a supplier from the directory.

| Item | Specification |
| --- | --- |
| Success status | `204 No Content` |
| Response body | None |
| Not found | **404** |

Permanently delete the TinyDB document for the given id.

---

## 7. Router Registration

In `app/main.py`, include the supplier router:

```python
from routes.suppliers import router as suppliers_router

app.include_router(suppliers_router)
```

Ensure `routes/` is importable when uvicorn runs from `services/api/` (package layout or `PYTHONPATH` as needed). Supplier routes use prefix `/suppliers` on the router itself, or mount without an extra prefix so paths match §6 exactly.

Existing incident routes under `/api/incidents/*` must remain unchanged.

---

## 8. Response Shape (`Supplier`)

Illustrative JSON (field names match `models.py`):

```json
{
  "id": 1,
  "name": "McKesson Medical Supplies",
  "country": "USA",
  "categories": ["medical_supplies"],
  "monthly_rate": 4200.0,
  "currency": "USD",
  "status": "active",
  "compliance_agreement": "BAA",
  "contract_renewal_date": "2025-06-30",
  "contact_email": "accounts@mckesson.com",
  "notes": "Primary clinical supplies provider for the 9 USA clinics.",
  "updated_at": "2026-08-05T18:30:00+00:00"
}
```

Enum and date fields serialise as strings in JSON. Omitted optional fields may be `null`.

---

## 9. Manual Verification

From `services/api/` after seeding:

```bash
uv run seed
uv run uvicorn app.main:app --reload --port 8000
```

| Action | Command |
| --- | --- |
| List all | `curl http://localhost:8000/suppliers` |
| Filter USA | `curl "http://localhost:8000/suppliers?country=USA"` |
| Filter category | `curl "http://localhost:8000/suppliers?category=clinical_software"` |
| Get by id | `curl http://localhost:8000/suppliers/1` |
| Create | `curl -X POST http://localhost:8000/suppliers -H "Content-Type: application/json" -d '{...}'` |
| Update rate | `curl -X PATCH http://localhost:8000/suppliers/1/rate -H "Content-Type: application/json" -d '{"monthly_rate": 4300}'` |
| Suspend | `curl -X PATCH http://localhost:8000/suppliers/1/status -H "Content-Type: application/json" -d '{"status": "suspended"}'` |
| Delete | `curl -X DELETE http://localhost:8000/suppliers/99` |

OpenAPI docs at [http://localhost:8000/docs](http://localhost:8000/docs) must list all six operations.

---

## 10. Acceptance Checklist

- [ ] `POST /suppliers` — Register a new supplier. Return the created supplier with its TinyDB-assigned ID. Reject invalid inputs with `422`.
- [ ] `GET /suppliers` — List all suppliers. Accept optional query parameters to filter by country and by product category. If no parameters are provided, return all.
- [ ] `GET /suppliers/{id}` — Return the detail of a supplier by ID. Return `404` if it does not exist.
- [ ] `PATCH /suppliers/{id}/rate` — Update a supplier's rate. Automatically record the `updated_at` timestamp at the time of the change. Do not accept rates equal to or less than zero.
- [ ] `PATCH /suppliers/{id}/status` — Activate or suspend a supplier. Accept only the two status values defined in the CONTEXT.
- [ ] `DELETE /suppliers/{id}` — Remove a supplier from the directory. Return `404` if the ID does not exist.
- [ ] Routes implemented in `routes/suppliers.py` and mounted from `app/main.py`
- [ ] Rate and create operations update `updated_at`; status-only changes do not

---

## 11. Out of Scope (Step 4+)

- General-purpose `PUT` / full `PATCH` for arbitrary field updates
- Authentication or authorisation

Step 4 frontend: `uis/backoffice/app/suppliers/` (BFF at `uis/backoffice/app/api/suppliers/`).
