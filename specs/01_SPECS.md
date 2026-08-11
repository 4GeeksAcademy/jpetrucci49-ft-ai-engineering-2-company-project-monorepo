# SPECS — Milestone 2: Programming Fundamentals

Specifications for the TypeScript data-processing utilities added in Milestone 2. Derived from `context/02_CONTEXT.md` and `milestones/02_README.md`.

---

## 1. Scope

Build the core data-processing logic layer for HealthCore's internal operations dashboard. This milestone adds **reusable, well-typed TypeScript utilities** — not a UI, not AI.

Three operational problems this code must support:

| Problem | Consumer | What the utilities must do |
| --- | --- | --- |
| Billing denial tracking | Tom Callahan, Revenue Cycle | Calculate denial rates by payer and location; flag high-denial payers |
| No-show cost estimation | Dr. Marcus Reid, Clinical Operations | Estimate weekly revenue lost to no-shows; flag high no-show locations |
| CME compliance monitoring | Diane Foster, People & Workforce | Generate CME reports; flag at-risk clinicians and expiring licences |

These numbers feed a Monday-morning operations report. Correctness and reliability are the priority.

---

## 2. Deliverables

### 2.1 Required

1. **TypeScript interfaces** for `Claim`, `Appointment`, `Clinician`, and `ClinicLocation` (defined in `src/types.d.ts`)
2. **Collection operations** — filter, sort, group arrays without mutating originals
3. **Search operations** — linear search on unsorted arrays; binary search on sorted arrays
4. **Transformations and aggregations** — denial rates, no-show costs/rates, CME reports
5. **Business validations** — verify records comply with rules before processing
6. **Type-check command** — e.g. `npm run typecheck` or `npx tsc --noEmit`

### 2.2 Optional

- HTML test page with Tailwind CSS to manually exercise functions (`utility-test.html`)
- Vitest unit tests in `tests/utils/`

### 2.3 Out of scope

- Dashboard UI
- AI / LLM integration
- Backend persistence or API endpoints

---

## 3. File Structure

```text
src/
├── types.d.ts             # Global interfaces and types (see §4)
├── utils/
│   ├── collections.ts     # Filter, sort, group
│   ├── search.ts          # Linear and binary search
│   ├── transformations.ts # Aggregations and reports
│   ├── validations.ts     # Business validations
│   └── index.ts           # Re-exports all utils
├── utility-test.ts        # Manual tester UI logic (optional)
└── utils-playground.ts    # CLI smoke script (optional)
tests/
└── utils/
    ├── fixtures.ts        # Typed sample data
    └── *.test.ts          # Vitest unit tests
```

Functions must live in the file that matches their responsibility.

### Type definitions (`src/types.d.ts`)

All entity interfaces and shared types are declared globally in `src/types.d.ts` using a `declare global` block. Utility modules consume these types without importing them — TypeScript picks them up automatically because the file is included in `tsconfig.json`.

Supporting types also defined there:

| Type | Purpose |
| --- | --- |
| `FilterType` | Partial filter object for `filterClaims` |
| `ValidationResult` | Return shape for `validateClaim` and `validateClinician` |
| `ConsultantFee` | `Record<ServiceType, number>` — fee map on `ClinicLocation` |

> **Note:** `context/02_CONTEXT.md` refers to this entity as `Location`. This project uses `ClinicLocation` to distinguish clinic records from generic location concepts.

---

## 4. Business Entities

### 4.1 Claim

A billing request submitted to an insurance payer after a patient visit.

```typescript
interface Claim {
  claimId: string;           // "CLM-XXXXXX"
  patientId: string;           // "HC-XXXXXX"
  locationId: string;          // e.g. "us-tx-001"
  serviceType: ServiceType;
  payerName: string;
  payerId: string;
  submissionDate: string;      // ISO 8601
  claimAmount: number;         // USD, must be > 0
  status: ClaimStatus;
  denialReason?: DenialReason; // required when status === "denied"
  resubmitted: boolean;
}

type ClaimStatus = "submitted" | "approved" | "denied" | "pending" | "appealed";

type DenialReason =
  | "missing_authorisation" | "coding_error" | "duplicate_claim"
  | "patient_not_covered" | "service_not_covered" | "incomplete_documentation";

type ServiceType =
  | "primary_care" | "chronic_disease" | "preventive" | "specialist"
  | "womens_health" | "paediatric" | "mental_health";
```

**Validation rules:**

- `claimAmount` > 0
- `submissionDate` not in the future
- `locationId` in known clinic IDs
- `denialReason` present when `status === "denied"`
- `patientId` matches `HC-` + 6 alphanumeric characters

### 4.2 Appointment

```typescript
interface Appointment {
  appointmentId: string;   // "APT-XXXXXX"
  patientId: string;
  locationId: string;
  serviceType: ServiceType;
  scheduledDate: string;   // ISO 8601
  scheduledTime: string;   // "HH:MM" 24-hour
  status: AppointmentStatus;
  noShowReason?: string;
  confirmedAt?: string;
}

type AppointmentStatus = "scheduled" | "confirmed" | "completed" | "no_show" | "cancelled";
```

**Validation rules:**

- `scheduledTime` valid 24-hour `"HH:MM"` format
- `locationId` in known clinic IDs
- If `status === "no_show"`, `noShowReason` should be present (warn if missing; do not reject)

### 4.3 Clinician

```typescript
interface Clinician {
  clinicianId: string;       // "CLN-XXXXXX"
  firstName: string;
  lastName: string;
  role: ClinicianRole;
  locationId: string;
  licenceState: string;      // US state code or "UK"
  licenceExpiryDate: string;
  cmeHoursRequired: number;
  cmeHoursLogged: number;
  cmeYearStartDate: string;
}

type ClinicianRole = "physician" | "nurse_practitioner" | "nurse" | "medical_assistant";
```

**Validation rules:**

- `cmeHoursRequired` and `cmeHoursLogged` ≥ 0
- `licenceExpiryDate` valid; past dates flagged as expired
- `role` one of the four defined values

### 4.4 ClinicLocation

A clinic record including average consultation fees used for no-show cost calculations.

```typescript
type ConsultantFee = Record<ServiceType, number>;

interface ClinicLocation {
  locationId: string;
  name: string;
  city: string;
  stateOrCountry: string;
  country: "US" | "UK";
  phone: string;
  averageConsultationFee: ConsultantFee; // USD per service type
}
```

---

## 5. Required Functions

### 5.1 Collections — `src/utils/collections.ts`

| Function | Signature | Behaviour |
| --- | --- | --- |
| `filterClaims` | `(claims: Claim[], filters: FilterType) → Claim[]` | Match **all** provided keys: `locationId`, `status`, `payerName`, `serviceType`. Ignore unset keys. |
| `filterAppointmentsByStatus` | `(appointments, statuses) → Appointment[]` | Match **any** of the provided statuses |
| `sortClaimsById` | `(claims, direction) → Claim[]` | Alphanumeric by `claimId`; do not mutate input |
| `sortAppointmentsByDate` | `(appointments, direction) → Appointment[]` | By `scheduledDate`; do not mutate input |
| `groupClaimsBy` | `(claims, key) → Record<string, Claim[]>` | Group by `locationId`, `payerName`, `status`, or `serviceType` |

### 5.2 Search — `src/utils/search.ts`

| Function | Signature | Behaviour |
| --- | --- | --- |
| `findClaimById` | `(claims, claimId) → Claim \| null` | Linear search |
| `findClinicianById` | `(clinicians, clinicianId) → Clinician \| null` | Linear search |
| `binarySearchClaimById` | `(sortedClaims, targetId) → number` | Binary search on `claimId`-sorted array; return index or `-1` |

### 5.3 Billing — `src/utils/transformations.ts`

| Function | Signature | Behaviour |
| --- | --- | --- |
| `calculateDenialRate` | `(claims) → number` | Percentage 0–100, 2 dp; only `"denied"` counts as denied; **throws** on empty array |
| `denialRateByPayer` | `(claims) → Record<string, number>` | Denial rate per payer, 2 dp |
| `denialRateByLocation` | `(claims) → Record<string, number>` | Denial rate per location, 2 dp |
| `flagHighDenialPayers` | `(claims, threshold?) → string[]` | Payer names above threshold (default **8%**) |

### 5.4 No-show — `src/utils/transformations.ts`

| Function | Signature | Behaviour |
| --- | --- | --- |
| `calculateNoShowCost` | `(appointments, location: ClinicLocation, weekEndingDate) → number` | Revenue lost to no-shows in the 7 calendar days ending on `weekEndingDate` (inclusive), using `location.averageConsultationFee[serviceType]`; USD, 2 dp; `0` if none |
| `noShowRateByLocation` | `(appointments) → Record<string, number>` | No-show rate per location, 2 dp |
| `flagHighNoShowLocations` | `(appointments, threshold?) → string[]` | Location IDs above threshold (default **20%**) |

### 5.5 CME — `src/utils/transformations.ts`

| Function | Signature | Behaviour |
| --- | --- | --- |
| `generateCMEReport` | `(clinicians, asOfDate) → CMEReport[]` | One entry per clinician (see §5.6) |
| `getCliniciansAtRisk` | `(clinicians, asOfDate) → Clinician[]` | `complianceStatus` is `"at_risk"` or `"overdue"` |
| `getCliniciansWithExpiringLicences` | `(clinicians, asOfDate, daysThreshold) → Clinician[]` | Licence expires within `daysThreshold` calendar days |

### 5.6 CME Report Type

```typescript
interface CMEReport {
  clinicianId: string;
  fullName: string;              // "${firstName} ${lastName}"
  role: ClinicianRole;
  locationId: string;
  hoursRequired: number;
  hoursLogged: number;
  hoursRemaining: number;        // Math.max(0, required - logged)
  percentComplete: number;       // (logged / required) * 100, 1 dp
  daysRemainingInCycle: number;  // calendar days from asOfDate to cycle end
  complianceStatus: CMEStatus;
  licenceExpiryDate: string;
  licenceDaysRemaining: number;
}

type CMEStatus = "on_track" | "at_risk" | "overdue" | "complete";
```

**Compliance status logic:**

| Status | Condition |
| --- | --- |
| `complete` | `hoursLogged >= hoursRequired` |
| `overdue` | CME cycle ended AND `hoursLogged < hoursRequired` |
| `at_risk` | Cycle active AND `percentComplete` is >15 pp behind elapsed share of year |
| `on_track` | Cycle active and not at risk |

### 5.7 Validations — `src/utils/validations.ts`

| Function | Signature | Behaviour |
| --- | --- | --- |
| `validateClaim` | `(claim, knownLocationIds) → ValidationResult` | All claim rules; one error message per failed rule |
| `validateClinician` | `(clinician) → ValidationResult` | All clinician rules |
| `isDenialRateAboveThreshold` | `(rate, threshold?) → boolean` | Default threshold **8%** |
| `isNoShowRateAboveThreshold` | `(rate, threshold?) → boolean` | Default threshold **20%** |

---

## 6. Business Rules & Thresholds

Encode these exactly — they appear on the Monday operations report.

| Rule | Value |
| --- | --- |
| Billing denial rate — industry benchmark | 8% |
| No-show rate — internal alert | 20% |
| CME hours required — Physician | 40 hrs/year |
| CME hours required — Nurse Practitioner | 30 hrs/year |
| CME "at risk" — trailing threshold | 15 percentage points behind cycle pace |
| Licence alert — first warning | 90 days before expiry |
| Licence alert — urgent | 30 days before expiry |

---

## 7. Code Quality Requirements

- **Explicit types** on all parameters and return values — no `any`
- **Global type declarations** in `src/types.d.ts` — entity interfaces are ambient; utility files do not import them
- **Pure functions** — no global state; only use inputs
- **No mutations** — sort/filter must not modify the original array
- **Single responsibility** — one job per function
- **Naming** — camelCase for functions/variables, PascalCase for interfaces
- **Edge cases** — empty arrays, not-found elements, division by zero, missing optional fields
- **Comments** — only for non-obvious logic

---

## 8. Acceptance Criteria

### Technical correctness

- [ ] Interfaces match spec field names and types
- [ ] Filtering returns elements matching all/any criteria as specified
- [ ] Sorting works ascending and descending without mutating input
- [ ] Linear search returns element or `null`
- [ ] Binary search returns correct index or `-1`
- [ ] Aggregations produce correct rates, costs, and reports
- [ ] Validations reject invalid data per business rules
- [ ] No TypeScript compilation errors
- [ ] Documented type-check command runs successfully

### Structure

- [ ] Types defined in `src/types.d.ts` with correct field names and union literals
- [ ] Code split by responsibility (`collections`, `search`, `transformations`, `validations`)
- [ ] Each function has a single identifiable responsibility

### Context fidelity

- [ ] Entity fields and types match `context/02_CONTEXT.md` (with `ClinicLocation` in place of `Location`)
- [ ] Thresholds and CME logic match the business rules table
- [ ] A generic implementation that ignores HealthCore-specific rules is not acceptable

---

## 9. Sample Data

Use the typed fixtures in `tests/utils/fixtures.ts` to verify implementations. The file exports:

- `locations: ClinicLocation[]`
- `claims: Claim[]`
- `appointments: Appointment[]`
- `clinicians: Clinician[]`

Field names and values must match the interfaces exactly. Known clinic IDs in sample data: `us-tx-001`, `us-fl-001`, `us-ga-001`.

---

## 10. Development Commands

| Command | Purpose |
| --- | --- |
| `npm run typecheck` | TypeScript validation |
| `npm test` | Run Vitest unit tests |
| `npm run utils:playground` | Run utility playground script |
| `npm run build:utility-test` | Bundle manual tester UI |

---

## References

- `context/02_CONTEXT.md` — entities, functions, validation rules, sample data
- `milestones/02_README.md` — milestone structure, evaluation checklist, submission steps
