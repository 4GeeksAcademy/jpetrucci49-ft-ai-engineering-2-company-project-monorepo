# SPECS — Milestone 6 (Step 1): Supplier Directory Data Model

Implementation specification for the HealthCore supplier registry **Pydantic models and validation rules**. Build exactly what is described below.

This is **step 1 of 4** for the Supplier Directory (FastAPI + TinyDB + Pydantic). Later steps will cover persistence, API routes, and frontend integration.

---

## 1. Objective

Define typed supplier models that enforce all business rules from `context/06_CONTEXT.md` **before** data is written to TinyDB. Invalid payloads must fail at validation time with clear field-level errors — not inside route handlers or the database layer.

---

## 2. Required Reading

| File | Use |
| --- | --- |
| `context/06_CONTEXT.md` | Field definitions, valid categories/statuses, country–currency rules, rate traceability |

---

## 3. Project Layout

Supplier Directory code in this milestone uses the following structure under the monorepo:

```text
services/
  api/
    main.py              ← FastAPI application
    models.py            ← Pydantic models (this step)
    database.py          ← TinyDB initialisation (later step)
    routes/
      suppliers.py       ← supplier directory endpoints (later step)
    seed.py              ← initial data loading script (later step)
uis/
  application/
    app/
      suppliers/         ← supplier directory page (later step)
```

**This document covers `models.py` only.** Endpoints live in `routes/suppliers.py`; persistence in `database.py`. Do not colocate models inside the routes module.

---

## 4. Location & Stack

| Item | Value |
| --- | --- |
| Module path | `services/api/models.py` |
| Language | Python 3.12+ |
| Validation | Pydantic v2 |
| Package manager | **uv** (`services/api/pyproject.toml`) |

Export enums and models from `models.py` for use by `database.py` and `routes/suppliers.py` in later steps.

---

## 5. Reference Data (Constants)

Define module-level constants (or `StrEnum` members) matching the context exactly.

### 5.1 Valid categories

```python
VALID_CATEGORIES = [
    "medical_supplies",
    "laboratory_services",
    "pharmaceutical",
    "clinical_software",
    "it_infrastructure",
    "hr_and_payroll_software",
    "cleaning_and_facilities",
    "patient_communication",
    "billing_and_coding_software",
    "training_platforms",
]
```

Every entry in `categories` must be one of these values. Reject unknown categories at validation time.

### 5.2 Valid statuses

```python
VALID_STATUSES = ["active", "suspended"]
```

Implement as a `StrEnum` (recommended) named `SupplierStatus`.

### 5.3 Country and currency

| `country` | Allowed `currency` |
| --- | --- |
| `"USA"` | `"USD"` only |
| `"UK"` | `"GBP"` only |

Implement country as a `StrEnum` (`SupplierCountry`). Currency may be a `StrEnum` (`SupplierCurrency`) or derived/validated against country — the API must **reject** mismatched pairs (e.g. `country="USA"` with `currency="GBP"`).

### 5.4 Compliance agreement

Optional field. When present, value must be exactly one of:

| Value | Meaning |
| --- | --- |
| `"BAA"` | USA business associate agreement |
| `"DPA"` | UK data processing agreement |
| `"both"` | Both agreements on file |
| `null` | Not applicable / not recorded |

Implement as `ComplianceAgreement` `StrEnum` plus `None`. Do **not** auto-require this field based on category (context treats that as operational guidance, not API validation).

---

## 6. Field Specification

| Field | Type | Required on create | Notes |
| --- | --- | --- | --- |
| `name` | `str` | ✅ | Non-empty after strip |
| `country` | `SupplierCountry` | ✅ | `"USA"` or `"UK"` |
| `categories` | `list[str]` | ✅ | Min length 1; each item ∈ `VALID_CATEGORIES` |
| `monthly_rate` | `float` | ✅ | Must be **> 0** (reject `0` and negatives) |
| `currency` | `SupplierCurrency` | ✅ | Must match `country` (see §5.3) |
| `status` | `SupplierStatus` | ✅ | `"active"` or `"suspended"` only |
| `compliance_agreement` | `ComplianceAgreement \| None` | ❌ | Default `None` |
| `contract_renewal_date` | `date \| None` | ❌ | ISO date `YYYY-MM-DD` when provided |
| `contact_email` | `str \| None` | ❌ | Valid email format when provided |
| `notes` | `str \| None` | ❌ | Free text |
| `updated_at` | `datetime` | — | **System-generated**; never accepted from client input |
| `id` | `int` | — | **System-generated** TinyDB document id; present on stored/read models only |

---

## 7. Pydantic Models

Use separate models so clients cannot set server-managed fields.

### 7.1 `SupplierBase`

Shared fields for create and full replace. Contains every client-supplied field from §6 **except** `id` and `updated_at`.

Validation on this base (or on models that inherit it):

- `name`: `min_length=1` after strip (use `@field_validator` or `Annotated` + `AfterValidator` to strip whitespace).
- `categories`: `@field_validator` — reject empty list; reject any value not in `VALID_CATEGORIES`.
- `monthly_rate`: `Field(gt=0)` — Pydantic must reject zero and negative values.
- `status`: `SupplierStatus` enum — reject any other string.
- `country` + `currency`: `@model_validator(mode="after")` — enforce §5.3 pairing.
- `contract_renewal_date`: parse as `date`; reject invalid date strings.
- `contact_email`: when not `None`, must be a valid email (`EmailStr` or equivalent).

### 7.2 `SupplierCreate`

Body model for registering a new supplier.

- Inherits `SupplierBase` (or duplicates its fields with same validators).
- **Must not** include `id` or `updated_at`.

On successful create (handled in a later step), the service sets `updated_at` to the current UTC timestamp.

### 7.3 `SupplierUpdate`

Body model for partial updates (used in later API steps).

- All fields optional except none are required.
- Same per-field validators as `SupplierBase` when a field **is** provided.
- **Must not** include `updated_at` — the service sets it when `monthly_rate` changes (see §8).
- If both `country` and `currency` are sent in the same payload, validate the pair. If only one is sent, the service layer must re-validate the combined record before save (document this expectation; full merge logic is step 2).

### 7.4 `SupplierRateUpdate`

Dedicated model for monthly rate changes (used in later API steps).

| Field | Type | Validation |
| --- | --- | --- |
| `monthly_rate` | `float` | `Field(gt=0)` |

**Must not** include `updated_at`. The service sets `updated_at` on apply.

### 7.5 `SupplierStatusUpdate`

Dedicated model for activate/suspend (used in later API steps).

| Field | Type | Validation |
| --- | --- | --- |
| `status` | `SupplierStatus` | `"active"` or `"suspended"` only |

### 7.6 `Supplier` (response / stored shape)

Full supplier record returned by the API and stored in TinyDB.

| Field | Source |
| --- | --- |
| `id` | TinyDB document id (`int`) |
| All `SupplierBase` fields | As validated |
| `updated_at` | Set by the system on create and on every `monthly_rate` change |

Configure with `model_config = ConfigDict(from_attributes=True)` if loading from dict/TinyDB documents.

**Must not** be used as a request body model.

---

## 8. Rate Traceability Rule

`updated_at` is **never** accepted from client payloads.

| Event | `updated_at` behaviour |
| --- | --- |
| Create supplier | Set to current UTC `datetime` |
| Update `monthly_rate` (via `SupplierRateUpdate` or `SupplierUpdate`) | Set to current UTC `datetime` |
| Update any other field without changing `monthly_rate` | Leave unchanged |
| Status change only | Leave unchanged |

Use timezone-aware UTC datetimes (`datetime.now(timezone.utc)` or equivalent).

---

## 9. Validation Examples (Must Reject)

The following must raise Pydantic `ValidationError` (or equivalent HTTP 422 when wired to routes in a later step):

| Payload issue | Example |
| --- | --- |
| Invalid status | `"status": "deleted"` |
| Non-positive rate | `"monthly_rate": 0` or `-100` |
| Empty categories | `"categories": []` |
| Unknown category | `"categories": ["unknown_service"]` |
| Country/currency mismatch | `country="USA"`, `currency="GBP"` |
| Client sends `updated_at` | Field excluded from input models — if forced via extra fields policy, reject |
| Invalid renewal date | `"contract_renewal_date": "31-06-2025"` |
| Invalid compliance value | `"compliance_agreement": "HIPAA"` |

---

## 10. Acceptance Checklist

- [ ] Define the Pydantic `Supplier` model with the required fields from the CONTEXT
- [ ] The `status` field must accept only the values defined in the CONTEXT. Use an `Enum` or a field validator to reject any other value.
- [ ] The rate field defined in the CONTEXT must be a positive number. Pydantic must reject zero or negative values before the data reaches TinyDB.
- [ ] Create separate input and response models where necessary (for example: the `updated_at` field is generated by the system, not sent by the client).
- [ ] `SupplierCreate`, `SupplierUpdate`, `SupplierRateUpdate`, and `SupplierStatusUpdate` do not expose `id` or `updated_at`
- [ ] `categories` enforces minimum length 1 and membership in `VALID_CATEGORIES`
- [ ] `country` / `currency` pairing enforced per CONTEXT
- [ ] `compliance_agreement` accepts only `BAA`, `DPA`, `both`, or `null`
- [ ] Models live in `services/api/models.py` and are importable by `database.py` and `routes/suppliers.py`

---

## 11. Out of Scope (Later Steps)

Implemented in subsequent milestone steps:

- `database.py` — TinyDB connection, file path, and CRUD operations (Step 2)
- `routes/suppliers.py` — REST endpoints including `DELETE` (Step 3)
- `seed.py` — loading initial supplier data from context (Step 2)
- `uis/backoffice/app/suppliers/` — frontend directory page (Step 4)

Note: `context/06_CONTEXT.md` describes suspension as the primary lifecycle action; the API and UI also expose hard delete for directory maintenance.
