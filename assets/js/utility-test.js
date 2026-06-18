// src/utils/collections.ts
function filterClaims(claims2, filters) {
  return claims2.filter(
    (claim) => Object.keys(filters).every((filter) => {
      const filterValue = filters[filter];
      if (filterValue === void 0) return true;
      return claim[filter] === filterValue;
    })
  );
}
function filterAppointmentsByStatus(appointments2, status) {
  if (status.length === 0) return [];
  const allowed = new Set(status);
  return appointments2.filter((appointment) => allowed.has(appointment.status));
}
function sortClaimsById(claims2, direction) {
  const sorted = [...claims2].sort((a, b) => a.claimId.localeCompare(b.claimId));
  return direction === "desc" ? sorted.reverse() : sorted;
}
function sortAppointmentsByDate(appointments2, direction) {
  const sorted = [...appointments2].sort((a, b) => {
    const dateCompare = a.scheduledDate.localeCompare(b.scheduledDate);
    if (dateCompare !== 0) return dateCompare;
    return a.scheduledTime.localeCompare(b.scheduledTime);
  });
  return direction === "desc" ? sorted.reverse() : sorted;
}
function groupClaimsBy(claims2, key) {
  return claims2.reduce((acc, claim) => {
    const groupKey = claim[key];
    if (!acc[groupKey]) acc[groupKey] = [];
    acc[groupKey].push(claim);
    return acc;
  }, {});
}

// src/utils/search.ts
function findClaimById(claims2, claimId) {
  const match = claims2.find((claim) => claim.claimId === claimId);
  return match ?? null;
}
function findClinicianById(clinicians2, clinicianId) {
  const match = clinicians2.find((clinician) => clinician.clinicianId === clinicianId);
  return match ?? null;
}
function binarySearchClaimById(sortedClaims, targetId) {
  let left = 0, right = sortedClaims.length - 1;
  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const currentId = sortedClaims[mid].claimId;
    const comparison = currentId.localeCompare(targetId);
    if (comparison === 0) return mid;
    if (comparison < 0) left = mid + 1;
    else right = mid - 1;
  }
  return -1;
}

// src/utils/transformations.ts
var roundTo = (value, decimals) => {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
};
var calculateRate = (total, matching) => total === 0 ? 0 : roundTo(matching / total * 100, 2);
var toUtcDate = (dateString) => /* @__PURE__ */ new Date(`${dateString}T00:00:00.000Z`);
var isValidDate = (date) => !Number.isNaN(date.getTime());
var daysBetween = (start, end) => {
  const msPerDay = 24 * 60 * 60 * 1e3;
  return Math.floor((end.getTime() - start.getTime()) / msPerDay);
};
var getCycleEndDate = (cmeYearStartDate) => {
  const cycleStart = toUtcDate(cmeYearStartDate);
  const cycleEnd = new Date(cycleStart.getTime());
  cycleEnd.setUTCFullYear(cycleEnd.getUTCFullYear() + 1);
  cycleEnd.setUTCDate(cycleEnd.getUTCDate() - 1);
  return cycleEnd;
};
var getComplianceStatus = (clinician, asOfDate) => {
  const cycleStart = toUtcDate(clinician.cmeYearStartDate);
  const cycleEnd = getCycleEndDate(clinician.cmeYearStartDate);
  if (clinician.cmeHoursLogged >= clinician.cmeHoursRequired) return "complete";
  if (asOfDate.getTime() > cycleEnd.getTime() && clinician.cmeHoursLogged < clinician.cmeHoursRequired) return "overdue";
  const totalCycleDays = Math.max(1, daysBetween(cycleStart, cycleEnd) + 1);
  const elapsedDays = Math.min(Math.max(daysBetween(cycleStart, asOfDate) + 1, 0), totalCycleDays);
  const elapsedPercent = elapsedDays / totalCycleDays * 100;
  const percentComplete = clinician.cmeHoursRequired === 0 ? 100 : clinician.cmeHoursLogged / clinician.cmeHoursRequired * 100;
  if (percentComplete < elapsedPercent - 15) return "at_risk";
  return "on_track";
};
function calculateDenialRate(claims2) {
  if (claims2.length === 0) {
    throw new Error("Cannot calculate denial rate for an empty claims array.");
  }
  const deniedCount = claims2.filter((claim) => claim.status === "denied").length;
  return calculateRate(claims2.length, deniedCount);
}
function denialRateByPayer(claims2) {
  const groups = claims2.reduce((acc, claim) => {
    if (!acc[claim.payerName]) acc[claim.payerName] = [];
    acc[claim.payerName].push(claim);
    return acc;
  }, {});
  return Object.fromEntries(
    Object.entries(groups).map(([payerName, payerClaims]) => {
      const deniedCount = payerClaims.filter((claim) => claim.status === "denied").length;
      return [payerName, calculateRate(payerClaims.length, deniedCount)];
    })
  );
}
function denialRateByLocation(claims2) {
  const groups = claims2.reduce((acc, claim) => {
    if (!acc[claim.locationId]) acc[claim.locationId] = [];
    acc[claim.locationId].push(claim);
    return acc;
  }, {});
  return Object.fromEntries(
    Object.entries(groups).map(([locationId, locationClaims]) => {
      const deniedCount = locationClaims.filter((claim) => claim.status === "denied").length;
      return [locationId, calculateRate(locationClaims.length, deniedCount)];
    })
  );
}
function flagHighDenialPayers(claims2, threshold = 8) {
  const byPayer = denialRateByPayer(claims2);
  return Object.entries(byPayer).filter(([, rate]) => rate > threshold).map(([payer]) => payer);
}
function calculateNoShowCost(appointments2, location, weekEndingDate) {
  const endDate = toUtcDate(weekEndingDate);
  if (!isValidDate(endDate)) {
    throw new Error("weekEndingDate must be a valid ISO date string.");
  }
  const startDate = new Date(endDate.getTime());
  startDate.setUTCDate(startDate.getUTCDate() - 6);
  const total = appointments2.filter((appointment) => {
    if (appointment.locationId !== location.locationId) return false;
    if (appointment.status !== "no_show") return false;
    const appointmentDate = toUtcDate(appointment.scheduledDate);
    return appointmentDate.getTime() >= startDate.getTime() && appointmentDate.getTime() <= endDate.getTime();
  }).reduce((sum, appointment) => {
    return sum + location.averageConsultationFee[appointment.serviceType];
  }, 0);
  return roundTo(total, 2);
}
function noShowRateByLocation(appointments2) {
  const groups = appointments2.reduce((acc, appointment) => {
    if (!acc[appointment.locationId]) acc[appointment.locationId] = [];
    acc[appointment.locationId].push(appointment);
    return acc;
  }, {});
  return Object.fromEntries(
    Object.entries(groups).map(([locationId, locationAppointments]) => {
      const noShowCount = locationAppointments.filter((appointment) => appointment.status === "no_show").length;
      return [locationId, calculateRate(locationAppointments.length, noShowCount)];
    })
  );
}
function flagHighNoShowLocations(appointments2, threshold = 20) {
  const rates = noShowRateByLocation(appointments2);
  return Object.entries(rates).filter(([, rate]) => rate > threshold).map(([locationId]) => locationId);
}
function generateCMEReport(clinicians2, asOfDate) {
  const asOf = toUtcDate(asOfDate);
  if (!isValidDate(asOf)) {
    throw new Error("asOfDate must be a valid ISO date string.");
  }
  return clinicians2.map((clinician) => {
    const hoursRemaining = Math.max(0, clinician.cmeHoursRequired - clinician.cmeHoursLogged);
    const percentComplete = clinician.cmeHoursRequired === 0 ? 100 : roundTo(clinician.cmeHoursLogged / clinician.cmeHoursRequired * 100, 1);
    const cycleEnd = getCycleEndDate(clinician.cmeYearStartDate);
    const daysRemainingInCycle = daysBetween(asOf, cycleEnd);
    const licenceExpiry = toUtcDate(clinician.licenceExpiryDate);
    const licenceDaysRemaining = daysBetween(asOf, licenceExpiry);
    return {
      clinicianId: clinician.clinicianId,
      fullName: `${clinician.firstName} ${clinician.lastName}`,
      role: clinician.role,
      locationId: clinician.locationId,
      hoursRequired: clinician.cmeHoursRequired,
      hoursLogged: clinician.cmeHoursLogged,
      hoursRemaining,
      percentComplete,
      daysRemainingInCycle,
      complianceStatus: getComplianceStatus(clinician, asOf),
      licenceExpiryDate: clinician.licenceExpiryDate,
      licenceDaysRemaining
    };
  });
}
function getCliniciansAtRisk(clinicians2, asOfDate) {
  const report = generateCMEReport(clinicians2, asOfDate);
  const atRiskIds = new Set(
    report.filter((item) => item.complianceStatus === "at_risk" || item.complianceStatus === "overdue").map((item) => item.clinicianId)
  );
  return clinicians2.filter((clinician) => atRiskIds.has(clinician.clinicianId));
}
function getCliniciansWithExpiringLicences(clinicians2, asOfDate, daysThreshold) {
  const asOf = toUtcDate(asOfDate);
  if (!isValidDate(asOf)) {
    throw new Error("asOfDate must be a valid ISO date string.");
  }
  return clinicians2.filter((clinician) => {
    const expiryDate = toUtcDate(clinician.licenceExpiryDate);
    if (!isValidDate(expiryDate)) return false;
    const remainingDays = daysBetween(asOf, expiryDate);
    return remainingDays >= 0 && remainingDays <= daysThreshold;
  });
}

// src/utils/validations.ts
var isValidDateString = (dateString) => {
  const date = /* @__PURE__ */ new Date(`${dateString}T00:00:00.000Z`);
  return !Number.isNaN(date.getTime());
};
var isFutureDate = (dateString) => {
  const now = /* @__PURE__ */ new Date();
  const todayUtc = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const date = /* @__PURE__ */ new Date(`${dateString}T00:00:00.000Z`);
  return date.getTime() > todayUtc.getTime();
};
function validateClaim(claim, knownLocationIds) {
  const errors = [];
  if (claim.claimAmount <= 0) errors.push("claimAmount must be greater than 0.");
  if (!isValidDateString(claim.submissionDate)) errors.push("submissionDate must be a valid ISO 8601 date string.");
  else if (isFutureDate(claim.submissionDate)) errors.push("submissionDate must not be a future date.");
  if (!knownLocationIds.includes(claim.locationId)) errors.push("locationId must match a known clinic ID.");
  if (claim.status === "denied" && !claim.denialReason) errors.push("denialReason is required when status is denied.");
  if (!/^HC-[A-Za-z0-9]{6}$/.test(claim.patientId)) errors.push("patientId must match the format HC- followed by 6 alphanumeric characters.");
  return {
    valid: errors.length === 0,
    errors
  };
}
function validateClinician(clinician) {
  const errors = [];
  if (clinician.cmeHoursRequired < 0) errors.push("cmeHoursRequired must be greater than or equal to 0.");
  if (clinician.cmeHoursLogged < 0) errors.push("cmeHoursLogged must be greater than or equal to 0.");
  const allowedRoles = /* @__PURE__ */ new Set(["physician", "nurse_practitioner", "nurse", "medical_assistant"]);
  if (!allowedRoles.has(clinician.role)) errors.push("role must be one of: physician, nurse_practitioner, nurse, medical_assistant.");
  if (!isValidDateString(clinician.licenceExpiryDate)) errors.push("licenceExpiryDate must be a valid ISO 8601 date string.");
  else {
    const now = /* @__PURE__ */ new Date();
    const todayUtc = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
    const expiryDate = /* @__PURE__ */ new Date(`${clinician.licenceExpiryDate}T00:00:00.000Z`);
    if (expiryDate.getTime() < todayUtc.getTime()) errors.push("licenceExpiryDate is expired.");
  }
  return {
    valid: errors.length === 0,
    errors
  };
}
function isDenialRateAboveThreshold(rate, threshold = 8) {
  return rate > threshold;
}
function isNoShowRateAboveThreshold(rate, threshold = 20) {
  return rate > threshold;
}

// tests/utils/fixtures.ts
var locations = [
  {
    locationId: "us-tx-001",
    name: "HealthCore Austin Central",
    city: "Austin",
    stateOrCountry: "TX",
    country: "US",
    phone: "(512) 340-8800",
    averageConsultationFee: {
      primary_care: 180,
      chronic_disease: 220,
      preventive: 150,
      specialist: 320,
      womens_health: 240,
      paediatric: 175,
      mental_health: 200
    }
  },
  {
    locationId: "us-fl-001",
    name: "HealthCore Miami",
    city: "Miami",
    stateOrCountry: "FL",
    country: "US",
    phone: "(305) 510-7700",
    averageConsultationFee: {
      primary_care: 195,
      chronic_disease: 235,
      preventive: 160,
      specialist: 340,
      womens_health: 255,
      paediatric: 185,
      mental_health: 215
    }
  },
  {
    locationId: "us-ga-001",
    name: "HealthCore Atlanta",
    city: "Atlanta",
    stateOrCountry: "GA",
    country: "US",
    phone: "(404) 330-9900",
    averageConsultationFee: {
      primary_care: 170,
      chronic_disease: 210,
      preventive: 145,
      specialist: 310,
      womens_health: 230,
      paediatric: 165,
      mental_health: 190
    }
  }
];
var claims = [
  {
    claimId: "CLM-000001",
    patientId: "HC-A3F291",
    locationId: "us-tx-001",
    serviceType: "primary_care",
    payerName: "BlueCross",
    payerId: "BC001",
    submissionDate: "2025-03-10",
    claimAmount: 180,
    status: "approved",
    resubmitted: false
  },
  {
    claimId: "CLM-000002",
    patientId: "HC-B7K442",
    locationId: "us-fl-001",
    serviceType: "specialist",
    payerName: "Aetna",
    payerId: "AET002",
    submissionDate: "2025-03-11",
    claimAmount: 340,
    status: "denied",
    denialReason: "missing_authorisation",
    resubmitted: false
  },
  {
    claimId: "CLM-000003",
    patientId: "HC-C2M881",
    locationId: "us-ga-001",
    serviceType: "chronic_disease",
    payerName: "Medicare",
    payerId: "MED003",
    submissionDate: "2025-03-12",
    claimAmount: 210,
    status: "approved",
    resubmitted: false
  },
  {
    claimId: "CLM-000004",
    patientId: "HC-D9P553",
    locationId: "us-tx-001",
    serviceType: "preventive",
    payerName: "BlueCross",
    payerId: "BC001",
    submissionDate: "2025-03-13",
    claimAmount: 150,
    status: "denied",
    denialReason: "coding_error",
    resubmitted: true
  },
  {
    claimId: "CLM-000005",
    patientId: "HC-E4Q117",
    locationId: "us-fl-001",
    serviceType: "mental_health",
    payerName: "Cigna",
    payerId: "CIG004",
    submissionDate: "2025-03-14",
    claimAmount: 215,
    status: "pending",
    resubmitted: false
  }
];
var appointments = [
  {
    appointmentId: "APT-000001",
    patientId: "HC-A3F291",
    locationId: "us-tx-001",
    serviceType: "primary_care",
    scheduledDate: "2025-03-10",
    scheduledTime: "09:00",
    status: "completed",
    confirmedAt: "2025-03-09T14:00:00Z"
  },
  {
    appointmentId: "APT-000002",
    patientId: "HC-F6R228",
    locationId: "us-fl-001",
    serviceType: "specialist",
    scheduledDate: "2025-03-11",
    scheduledTime: "11:30",
    status: "no_show",
    noShowReason: "Patient did not call to cancel"
  },
  {
    appointmentId: "APT-000003",
    patientId: "HC-G1S774",
    locationId: "us-tx-001",
    serviceType: "chronic_disease",
    scheduledDate: "2025-03-12",
    scheduledTime: "14:00",
    status: "no_show",
    noShowReason: "Unreachable before appointment"
  },
  {
    appointmentId: "APT-000004",
    patientId: "HC-H8T390",
    locationId: "us-ga-001",
    serviceType: "preventive",
    scheduledDate: "2025-03-13",
    scheduledTime: "10:00",
    status: "completed",
    confirmedAt: "2025-03-12T09:30:00Z"
  },
  {
    appointmentId: "APT-000005",
    patientId: "HC-I5U661",
    locationId: "us-fl-001",
    serviceType: "mental_health",
    scheduledDate: "2025-03-14",
    scheduledTime: "16:00",
    status: "no_show",
    noShowReason: "Transportation issue reported"
  }
];
var clinicians = [
  {
    clinicianId: "CLN-000001",
    firstName: "Marcus",
    lastName: "Reid",
    role: "physician",
    locationId: "us-tx-001",
    licenceState: "TX",
    licenceExpiryDate: "2026-06-30",
    cmeHoursRequired: 40,
    cmeHoursLogged: 28,
    cmeYearStartDate: "2025-01-01"
  },
  {
    clinicianId: "CLN-000002",
    firstName: "Sandra",
    lastName: "Flores",
    role: "nurse_practitioner",
    locationId: "us-fl-001",
    licenceState: "FL",
    licenceExpiryDate: "2025-05-15",
    cmeHoursRequired: 30,
    cmeHoursLogged: 6,
    cmeYearStartDate: "2025-01-01"
  },
  {
    clinicianId: "CLN-000003",
    firstName: "David",
    lastName: "Okafor",
    role: "physician",
    locationId: "us-ga-001",
    licenceState: "GA",
    licenceExpiryDate: "2027-01-01",
    cmeHoursRequired: 40,
    cmeHoursLogged: 40,
    cmeYearStartDate: "2025-01-01"
  }
];

// src/utility-test.ts
function requireElement(id) {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Utility tester page is missing required DOM element: #${id}`);
  }
  return element;
}
var fields = [
  ["data-format", new HTMLSelectElement()],
  ["utility-function", new HTMLSelectElement()],
  ["test-data-input", new HTMLTextAreaElement()],
  ["test-data-file", new HTMLInputElement()],
  ["run-test", new HTMLButtonElement()],
  ["load-template", new HTMLButtonElement()],
  ["clear-test", new HTMLButtonElement()],
  ["test-result", new HTMLElement()],
  ["test-status", new HTMLElement()],
  ["function-hint", new HTMLElement()]
];
var formFields = fields.map(([id, type]) => requireElement(id));
console.log({ formFields });
var formatSelect = requireElement("data-format");
var functionSelect = requireElement("utility-function");
var textInput = requireElement("test-data-input");
var fileInput = requireElement("test-data-file");
var runButton = requireElement("run-test");
var templateButton = requireElement("load-template");
var clearButton = requireElement("clear-test");
var resultBox = requireElement("test-result");
var statusBox = requireElement("test-status");
var hintBox = requireElement("function-hint");
var i18n = {
  en: {
    ready: "Ready to run.",
    loaded: "Data loaded from file.",
    noFunction: "Select a utility function first.",
    noData: "Provide input data in the textarea or upload a file.",
    unsupported: "Unsupported file type. Use JSON, CSV, TSV, YAML, or TXT.",
    parseError: "Could not parse input data:",
    runOk: "Function executed successfully.",
    runError: "Function execution failed:",
    templateLoaded: "Template loaded for selected function.",
    templateMissing: "No template found for this function.",
    templateTitle: "Input template:",
    hintPrefix: "Expected input:",
    missingAsOfDate: "For this function, provide an asOfDate value (YYYY-MM-DD)."
  },
  es: {
    ready: "Listo para ejecutar.",
    loaded: "Datos cargados desde archivo.",
    noFunction: "Selecciona una funcion utilitaria primero.",
    noData: "Proporciona datos de entrada en el area de texto o sube un archivo.",
    unsupported: "Tipo de archivo no soportado. Usa JSON, CSV, TSV, YAML o TXT.",
    parseError: "No se pudieron interpretar los datos de entrada:",
    runOk: "Funcion ejecutada correctamente.",
    runError: "La ejecucion de la funcion fallo:",
    templateLoaded: "Plantilla cargada para la funcion seleccionada.",
    templateMissing: "No se encontro plantilla para esta funcion.",
    templateTitle: "Plantilla de entrada:",
    hintPrefix: "Entrada esperada:",
    missingAsOfDate: "Para esta funcion, proporciona un valor asOfDate (YYYY-MM-DD)."
  }
};
function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
var functionCatalog = {
  filterClaims: {
    hint: {
      en: '{ "claims": [...], "filters": { "payerName": "BlueCross" } }',
      es: '{ "claims": [...], "filters": { "payerName": "BlueCross" } }'
    },
    template: { claims: [], filters: { payerName: "BlueCross" } },
    run: (input) => filterClaims(input.claims, input.filters)
  },
  filterAppointmentsByStatus: {
    hint: {
      en: '{ "appointments": [...], "status": ["no_show", "completed"] }',
      es: '{ "appointments": [...], "status": ["no_show", "completed"] }'
    },
    template: { appointments: [], status: ["no_show", "completed"] },
    run: (input) => filterAppointmentsByStatus(input.appointments, input.status)
  },
  sortClaimsById: {
    hint: {
      en: '{ "claims": [...], "direction": "asc" }',
      es: '{ "claims": [...], "direction": "asc" }'
    },
    template: { claims: [], direction: "asc" },
    run: (input) => sortClaimsById(input.claims, input.direction)
  },
  sortAppointmentsByDate: {
    hint: {
      en: '{ "appointments": [...], "direction": "asc" }',
      es: '{ "appointments": [...], "direction": "asc" }'
    },
    template: { appointments: [], direction: "asc" },
    run: (input) => sortAppointmentsByDate(input.appointments, input.direction)
  },
  groupClaimsBy: {
    hint: {
      en: '{ "claims": [...], "key": "payerName" }',
      es: '{ "claims": [...], "key": "payerName" }'
    },
    template: { claims: [], key: "payerName" },
    run: (input) => groupClaimsBy(input.claims, input.key)
  },
  findClaimById: {
    hint: {
      en: '{ "claims": [...], "claimId": "CLM-000001" }',
      es: '{ "claims": [...], "claimId": "CLM-000001" }'
    },
    template: { claims: [], claimId: "CLM-000001" },
    run: (input) => findClaimById(input.claims, input.claimId)
  },
  findClinicianById: {
    hint: {
      en: '{ "clinicians": [...], "clinicianId": "CLN-000001" }',
      es: '{ "clinicians": [...], "clinicianId": "CLN-000001" }'
    },
    template: { clinicians: [], clinicianId: "CLN-000001" },
    run: (input) => findClinicianById(input.clinicians, input.clinicianId)
  },
  binarySearchClaimById: {
    hint: {
      en: '{ "sortedClaims": [...], "targetId": "CLM-000001" }',
      es: '{ "sortedClaims": [...], "targetId": "CLM-000001" }'
    },
    template: { sortedClaims: [], targetId: "CLM-000001" },
    run: (input) => binarySearchClaimById(input.sortedClaims, input.targetId)
  },
  calculateDenialRate: {
    hint: { en: '{ "claims": [...] }', es: '{ "claims": [...] }' },
    template: { claims: [] },
    run: (input) => calculateDenialRate(input.claims)
  },
  denialRateByPayer: {
    hint: { en: '{ "claims": [...] }', es: '{ "claims": [...] }' },
    template: { claims: [] },
    run: (input) => denialRateByPayer(input.claims)
  },
  denialRateByLocation: {
    hint: { en: '{ "claims": [...] }', es: '{ "claims": [...] }' },
    template: { claims: [] },
    run: (input) => denialRateByLocation(input.claims)
  },
  flagHighDenialPayers: {
    hint: { en: '{ "claims": [...], "threshold": 8 }', es: '{ "claims": [...], "threshold": 8 }' },
    template: { claims: [], threshold: 8 },
    run: (input) => flagHighDenialPayers(input.claims, input.threshold)
  },
  calculateNoShowCost: {
    hint: {
      en: '{ "appointments": [...], "location": {...}, "weekEndingDate": "2025-03-11" }',
      es: '{ "appointments": [...], "location": {...}, "weekEndingDate": "2025-03-11" }'
    },
    template: {
      appointments: [],
      location: {
        locationId: "us-tx-001",
        name: "HealthCore Austin Central",
        city: "Austin",
        stateOrCountry: "TX",
        country: "US",
        phone: "(512) 340-8800",
        averageConsultationFee: {
          primary_care: 180,
          chronic_disease: 220,
          preventive: 150,
          specialist: 320,
          womens_health: 240,
          paediatric: 175,
          mental_health: 200
        }
      },
      weekEndingDate: "2025-03-11"
    },
    run: (input) => calculateNoShowCost(input.appointments, input.location, input.weekEndingDate)
  },
  noShowRateByLocation: {
    hint: { en: '{ "appointments": [...] }', es: '{ "appointments": [...] }' },
    template: { appointments: [] },
    run: (input) => noShowRateByLocation(input.appointments)
  },
  flagHighNoShowLocations: {
    hint: { en: '{ "appointments": [...], "threshold": 20 }', es: '{ "appointments": [...], "threshold": 20 }' },
    template: { appointments: [], threshold: 20 },
    run: (input) => flagHighNoShowLocations(input.appointments, input.threshold)
  },
  generateCMEReport: {
    hint: { en: '{ "clinicians": [...], "asOfDate": "2025-06-30" }', es: '{ "clinicians": [...], "asOfDate": "2025-06-30" }' },
    template: { clinicians: [], asOfDate: "2025-06-30" },
    run: (input) => generateCMEReport(input.clinicians, input.asOfDate)
  },
  getCliniciansAtRisk: {
    hint: { en: '{ "clinicians": [...], "asOfDate": "2025-06-30" }', es: '{ "clinicians": [...], "asOfDate": "2025-06-30" }' },
    template: { clinicians: [], asOfDate: "2025-06-30" },
    run: (input) => getCliniciansAtRisk(input.clinicians, input.asOfDate)
  },
  getCliniciansWithExpiringLicences: {
    hint: { en: '{ "clinicians": [...], "asOfDate": "2025-06-30", "daysThreshold": 45 }', es: '{ "clinicians": [...], "asOfDate": "2025-06-30", "daysThreshold": 45 }' },
    template: { clinicians: [], asOfDate: "2025-06-30", daysThreshold: 45 },
    run: (input) => getCliniciansWithExpiringLicences(input.clinicians, input.asOfDate, input.daysThreshold)
  },
  validateClaim: {
    hint: { en: '{ "claim": {...}, "knownLocationIds": ["us-tx-001", "us-fl-001"] }', es: '{ "claim": {...}, "knownLocationIds": ["us-tx-001", "us-fl-001"] }' },
    template: {
      claim: {
        claimId: "CLM-000001",
        patientId: "HC-A3F291",
        locationId: "us-tx-001",
        serviceType: "primary_care",
        payerName: "BlueCross",
        payerId: "BC001",
        submissionDate: "2025-03-10",
        claimAmount: 180,
        status: "approved",
        resubmitted: false
      },
      knownLocationIds: ["us-tx-001", "us-fl-001"]
    },
    run: (input) => validateClaim(input.claim, input.knownLocationIds)
  },
  validateClinician: {
    hint: { en: '{ "clinician": {...} }', es: '{ "clinician": {...} }' },
    template: {
      clinician: {
        clinicianId: "CLN-000001",
        firstName: "Marcus",
        lastName: "Reid",
        role: "physician",
        locationId: "us-tx-001",
        licenceState: "TX",
        licenceExpiryDate: "2026-06-30",
        cmeHoursRequired: 40,
        cmeHoursLogged: 28,
        cmeYearStartDate: "2025-01-01"
      }
    },
    run: (input) => validateClinician(input.clinician)
  },
  isDenialRateAboveThreshold: {
    hint: { en: '{ "rate": 9.2, "threshold": 8 }', es: '{ "rate": 9.2, "threshold": 8 }' },
    template: { rate: 9.2, threshold: 8 },
    run: (input) => isDenialRateAboveThreshold(input.rate, input.threshold)
  },
  isNoShowRateAboveThreshold: {
    hint: { en: '{ "rate": 21, "threshold": 20 }', es: '{ "rate": 21, "threshold": 20 }' },
    template: { rate: 21, threshold: 20 },
    run: (input) => isNoShowRateAboveThreshold(input.rate, input.threshold)
  }
};
var fixtureTemplates = {
  filterClaims: {
    claims: clone(claims),
    filters: { payerName: "BlueCross" }
  },
  filterAppointmentsByStatus: {
    appointments: clone(appointments),
    status: ["no_show", "completed"]
  },
  sortClaimsById: {
    claims: clone(claims),
    direction: "asc"
  },
  sortAppointmentsByDate: {
    appointments: clone(appointments),
    direction: "asc"
  },
  groupClaimsBy: {
    claims: clone(claims),
    key: "payerName"
  },
  findClaimById: {
    claims: clone(claims),
    claimId: claims[1]?.claimId
  },
  findClinicianById: {
    clinicians: clone(clinicians),
    clinicianId: clinicians[0]?.clinicianId
  },
  binarySearchClaimById: {
    sortedClaims: clone(sortClaimsById(claims, "asc")),
    targetId: claims[2]?.claimId
  },
  calculateDenialRate: {
    claims: clone(claims)
  },
  denialRateByPayer: {
    claims: clone(claims)
  },
  denialRateByLocation: {
    claims: clone(claims)
  },
  flagHighDenialPayers: {
    claims: clone(claims),
    threshold: 40
  },
  calculateNoShowCost: {
    appointments: clone(appointments),
    location: clone(locations[0]),
    weekEndingDate: "2025-03-12"
  },
  noShowRateByLocation: {
    appointments: clone(appointments)
  },
  flagHighNoShowLocations: {
    appointments: clone(appointments),
    threshold: 70
  },
  generateCMEReport: {
    clinicians: clone(clinicians),
    asOfDate: "2025-06-15"
  },
  getCliniciansAtRisk: {
    clinicians: clone(clinicians),
    asOfDate: "2025-12-15"
  },
  getCliniciansWithExpiringLicences: {
    clinicians: clone(clinicians),
    asOfDate: "2025-06-15",
    daysThreshold: 30
  },
  validateClaim: {
    claim: clone(claims[1]),
    knownLocationIds: locations.map((location) => location.locationId)
  },
  validateClinician: {
    clinician: clone(clinicians[0])
  },
  isDenialRateAboveThreshold: {
    rate: 9.2,
    threshold: 8
  },
  isNoShowRateAboveThreshold: {
    rate: 21,
    threshold: 20
  }
};
Object.entries(fixtureTemplates).forEach(([functionName, template]) => {
  if (functionCatalog[functionName]) {
    functionCatalog[functionName].template = template;
  }
});
function getCurrentLang() {
  return document.documentElement.getAttribute("data-current-lang") === "es" ? "es" : "en";
}
function t(key) {
  return i18n[getCurrentLang()][key];
}
function stringifyResult(value) {
  if (value === void 0) return "undefined";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
function parseScalar(raw) {
  const value = raw.trim();
  if (value === "") return "";
  if (value === "true") return true;
  if (value === "false") return false;
  if (value === "null") return null;
  if (value === "undefined") return void 0;
  if (!Number.isNaN(Number(value)) && /^-?\d+(\.\d+)?$/.test(value)) return Number(value);
  const quoted = value.match(/^(?:["'])(.*)(?:["'])$/);
  return quoted ? quoted[1] : value;
}
function parseDelimitedLine(line, delimiter) {
  const values = [];
  let current = "";
  let inQuotes = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const nextChar = line[index + 1];
    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (char === delimiter && !inQuotes) {
      values.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  values.push(current);
  return values;
}
function stripTrailingCommas(text) {
  return text.replace(/,\s*([}\]])/g, "$1");
}
function parseJsonLike(text) {
  try {
    return JSON.parse(text);
  } catch (jsonError) {
    const sanitized = stripTrailingCommas(text);
    if (sanitized === text) throw jsonError;
    return JSON.parse(sanitized);
  }
}
function parseMaybeStructuredValue(raw) {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (/^[\[{]/.test(trimmed)) {
    try {
      return parseJsonLike(trimmed);
    } catch {
      return parseScalar(raw);
    }
  }
  return parseScalar(raw);
}
function toCamelCase(value) {
  return value.trim().replace(/^[A-Z]/, (char) => char.toLowerCase()).replace(/[_-]+([a-zA-Z0-9])/g, (_, char) => char.toUpperCase());
}
function normalizeRecordKeys(record) {
  return Object.fromEntries(Object.entries(record).map(([key, value]) => [toCamelCase(String(key)), value]));
}
function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function parseCsv(text, delimiter) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 2) throw new Error("CSV input must include a header row and at least one data row.");
  if (!lines[0].includes(delimiter)) throw new Error("CSV input must include a delimited header row.");
  const headers = parseDelimitedLine(lines[0], delimiter).map((header) => header.trim());
  if (headers.some((header) => header.length === 0)) throw new Error("CSV input contains an empty header value.");
  return lines.slice(1).map((line) => {
    if (!line.includes(delimiter)) throw new Error("CSV rows must match the header delimiter format.");
    const values = parseDelimitedLine(line, delimiter);
    if (values.length !== headers.length) {
      throw new Error("CSV rows must have the same number of columns as the header.");
    }
    const row = {};
    headers.forEach((header, index) => {
      row[header] = parseMaybeStructuredValue(values[index] ?? "");
    });
    return normalizeRecordKeys(row);
  });
}
function normalizeDateValue(value) {
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value.toISOString().slice(0, 10);
  return value;
}
function sanitizeParsedInput(value) {
  const normalized = normalizeDateValue(value);
  if (Array.isArray(normalized)) return normalized.map((item) => sanitizeParsedInput(item));
  if (isPlainObject(normalized)) {
    return Object.fromEntries(Object.entries(normalized).map(([key, entry]) => [key, sanitizeParsedInput(entry)]));
  }
  return normalized;
}
function firstNonEmpty(rows, key) {
  for (const row of rows) {
    const value = row[key];
    if (value === void 0 || value === null) continue;
    if (typeof value === "string" && value.trim() === "") continue;
    return value;
  }
  return void 0;
}
function toNumberOrFallback(value, fallback) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : fallback;
}
function splitListValue(value) {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value !== "string") return [];
  return value.split(/[|,;]/).map((item) => item.trim()).filter(Boolean);
}
function stripFields(record, fields2) {
  const output = { ...record };
  fields2.forEach((field) => {
    delete output[field];
  });
  return output;
}
function normalizeTableInput(functionName, rows) {
  const normalizedRows = rows.map((row) => normalizeRecordKeys(row));
  if (normalizedRows.length === 0) return { input: [] };
  const keyValueRows = normalizedRows.every(
    (row) => isPlainObject(row) && Object.keys(row).length === 2 && "key" in row && "value" in row
  );
  if (keyValueRows) {
    return normalizedRows.reduce((acc, row) => {
      const key = String(row.key ?? "").trim();
      if (!key) return acc;
      acc[toCamelCase(key)] = row.value;
      return acc;
    }, {});
  }
  switch (functionName) {
    case "generateCMEReport":
    case "getCliniciansAtRisk": {
      const asOfDate = firstNonEmpty(normalizedRows, "asOfDate");
      if (!asOfDate) throw new Error(t("missingAsOfDate"));
      return { clinicians: normalizedRows.map((row) => stripFields(row, ["asOfDate"])), asOfDate };
    }
    case "getCliniciansWithExpiringLicences": {
      const asOfDate = firstNonEmpty(normalizedRows, "asOfDate");
      if (!asOfDate) throw new Error(t("missingAsOfDate"));
      return {
        clinicians: normalizedRows.map((row) => stripFields(row, ["asOfDate", "daysThreshold"])),
        asOfDate,
        daysThreshold: toNumberOrFallback(firstNonEmpty(normalizedRows, "daysThreshold"), 45)
      };
    }
    case "calculateDenialRate":
    case "denialRateByPayer":
    case "denialRateByLocation":
    case "flagHighDenialPayers":
      return {
        claims: normalizedRows.map((row) => stripFields(row, ["threshold"])),
        threshold: toNumberOrFallback(firstNonEmpty(normalizedRows, "threshold"), 8)
      };
    case "filterClaims": {
      const filterKeys = ["locationId", "status", "payerName", "serviceType"];
      const filters = Object.fromEntries(
        filterKeys.map((key) => [key, firstNonEmpty(normalizedRows, key)]).filter(([, value]) => value !== void 0)
      );
      return { claims: normalizedRows.map((row) => stripFields(row, filterKeys)), filters };
    }
    case "findClaimById":
    case "binarySearchClaimById": {
      const claimId = firstNonEmpty(normalizedRows, "claimId") || firstNonEmpty(normalizedRows, "targetId");
      return {
        claims: normalizedRows.map((row) => stripFields(row, ["claimId", "targetId"])),
        sortedClaims: normalizedRows.map((row) => stripFields(row, ["claimId", "targetId"])),
        claimId,
        targetId: claimId
      };
    }
    case "validateClaim": {
      const first = normalizedRows[0];
      return { claim: stripFields(first, ["knownLocationIds"]), knownLocationIds: splitListValue(first.knownLocationIds) };
    }
    case "findClinicianById": {
      const clinicianId = firstNonEmpty(normalizedRows, "clinicianId");
      return { clinicians: normalizedRows.map((row) => stripFields(row, ["clinicianId"])), clinicianId };
    }
    case "validateClinician":
      return { clinician: normalizedRows[0] };
    case "noShowRateByLocation":
    case "flagHighNoShowLocations":
    case "filterAppointmentsByStatus":
    case "sortAppointmentsByDate":
      return {
        appointments: normalizedRows.map((row) => stripFields(row, ["threshold", "status", "direction"])),
        threshold: toNumberOrFallback(firstNonEmpty(normalizedRows, "threshold"), 20),
        status: splitListValue(firstNonEmpty(normalizedRows, "status")),
        direction: firstNonEmpty(normalizedRows, "direction") || "asc"
      };
    case "calculateNoShowCost": {
      const weekEndingDate = firstNonEmpty(normalizedRows, "weekEndingDate");
      const location = {
        locationId: firstNonEmpty(normalizedRows, "locationId"),
        name: firstNonEmpty(normalizedRows, "locationName") || firstNonEmpty(normalizedRows, "name"),
        city: firstNonEmpty(normalizedRows, "city"),
        stateOrCountry: firstNonEmpty(normalizedRows, "stateOrCountry"),
        country: firstNonEmpty(normalizedRows, "country"),
        phone: firstNonEmpty(normalizedRows, "phone"),
        averageConsultationFee: {}
      };
      return {
        appointments: normalizedRows.map(
          (row) => stripFields(row, ["weekEndingDate", "locationName", "name", "city", "stateOrCountry", "country", "phone"])
        ),
        location,
        weekEndingDate
      };
    }
    case "sortClaimsById":
      return {
        claims: normalizedRows.map((row) => stripFields(row, ["direction"])),
        direction: firstNonEmpty(normalizedRows, "direction") || "asc"
      };
    case "groupClaimsBy":
      return {
        claims: normalizedRows.map((row) => stripFields(row, ["key"])),
        key: firstNonEmpty(normalizedRows, "key") || "payerName"
      };
    case "isDenialRateAboveThreshold":
    case "isNoShowRateAboveThreshold":
      return {
        rate: toNumberOrFallback(firstNonEmpty(normalizedRows, "rate"), 0),
        threshold: toNumberOrFallback(firstNonEmpty(normalizedRows, "threshold"), functionName === "isDenialRateAboveThreshold" ? 8 : 20)
      };
    default:
      return { input: normalizedRows };
  }
}
async function parseYaml(text) {
  const yamlModuleUrl = "https://cdn.jsdelivr.net/npm/js-yaml@4.1.0/+esm";
  const module = await import(yamlModuleUrl);
  return module.load(text);
}
function inferFormat(fileName) {
  const extension = fileName.toLowerCase().split(".").pop() ?? "";
  if (extension === "json") return "json";
  if (extension === "csv") return "csv";
  if (extension === "tsv") return "tsv";
  if (extension === "yaml" || extension === "yml") return "yaml";
  if (extension === "txt") return "text";
  return "auto";
}
function looksLikeDelimitedText(text, delimiter) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 2) return false;
  try {
    const headerColumns = parseDelimitedLine(lines[0], delimiter);
    const firstRowColumns = parseDelimitedLine(lines[1], delimiter);
    return headerColumns.length > 1 && headerColumns.length === firstRowColumns.length;
  } catch {
    return false;
  }
}
async function parseByFormat(rawText, format) {
  const text = rawText.trim();
  if (!text) return null;
  if (format === "json") return parseJsonLike(text);
  if (format === "csv") return parseCsv(text, ",");
  if (format === "tsv") return parseCsv(text, "	");
  if (format === "yaml") return parseYaml(text);
  if (format === "text") return text;
  const looksStructured = /^[\[{]/.test(text);
  if (looksLikeDelimitedText(text, ",")) return parseCsv(text, ",");
  if (looksLikeDelimitedText(text, "	")) return parseCsv(text, "	");
  try {
    return parseJsonLike(text);
  } catch (jsonError) {
    try {
      return await parseYaml(text);
    } catch {
      if (looksStructured) throw jsonError;
      try {
        return parseCsv(text, ",");
      } catch {
        return text;
      }
    }
  }
}
function setStatus(kind, message) {
  const baseClass = "mt-3 rounded-md border p-3 text-sm";
  const variantClass = kind === "error" ? "border-red-300 bg-red-50 text-red-800" : kind === "success" ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-slate-300 bg-slate-50 text-slate-800";
  statusBox.className = `${baseClass} ${variantClass}`;
  statusBox.textContent = message;
}
function updateHint() {
  const selected = functionCatalog[functionSelect.value];
  if (!selected) {
    hintBox.textContent = "";
    return;
  }
  const isDelimited = formatSelect.value === "csv" || formatSelect.value === "tsv";
  const csvHint = isDelimited ? ` ${getCurrentLang() === "es" ? "Tambien puedes usar formato key,value para argumentos sueltos." : "You can also use key,value format for scalar arguments."}` : "";
  hintBox.textContent = `${t("hintPrefix")} ${selected.hint[getCurrentLang()]}${csvHint}`;
}
async function getInputPayload() {
  const selectedFile = fileInput.files?.[0] ?? null;
  const selectedFormat = formatSelect.value;
  if (selectedFile) {
    const fileText = await selectedFile.text();
    const format = selectedFormat === "auto" ? inferFormat(selectedFile.name) : selectedFormat;
    if (format === "auto") throw new Error(t("unsupported"));
    return sanitizeParsedInput(await parseByFormat(fileText, format));
  }
  const inlineText = textInput.value.trim();
  if (!inlineText) throw new Error(t("noData"));
  return sanitizeParsedInput(await parseByFormat(inlineText, selectedFormat));
}
function normalizeInputForFunction(functionName, rawInput) {
  if (Array.isArray(rawInput)) return normalizeTableInput(functionName, rawInput);
  if (rawInput && typeof rawInput === "object") return rawInput;
  return { input: rawInput };
}
function loadTemplate() {
  const selected = functionCatalog[functionSelect.value];
  if (!selected) {
    setStatus("error", t("noFunction"));
    return;
  }
  textInput.value = JSON.stringify(selected.template, null, 2);
  setStatus("info", `${t("templateTitle")} ${t("templateLoaded")}`);
}
function autofillTemplateForSelection() {
  const selected = functionCatalog[functionSelect.value];
  if (!selected) {
    textInput.value = "";
    return;
  }
  textInput.value = JSON.stringify(selected.template, null, 2);
}
async function runSelectedFunction() {
  const selected = functionCatalog[functionSelect.value];
  if (!selected) {
    setStatus("error", t("noFunction"));
    return;
  }
  try {
    const parsedInput = await getInputPayload();
    const normalizedInput = normalizeInputForFunction(functionSelect.value, parsedInput);
    const result = selected.run(normalizedInput);
    resultBox.textContent = stringifyResult(result);
    setStatus("success", t("runOk"));
  } catch (error) {
    resultBox.textContent = "";
    const base = error instanceof Error ? error.message : String(error);
    const messagePrefix = /Unexpected token|JSON|YAML|CSV|format|delimiter|header|column/i.test(base) ? t("parseError") : t("runError");
    setStatus("error", `${messagePrefix} ${base}`);
  }
}
function clearAll() {
  textInput.value = "";
  fileInput.value = "";
  resultBox.textContent = "";
  setStatus("info", t("ready"));
}
function handleFileChange() {
  if (!fileInput.files?.[0]) return;
  setStatus("info", t("loaded"));
}
functionSelect.addEventListener("change", () => {
  updateHint();
  autofillTemplateForSelection();
});
formatSelect.addEventListener("change", updateHint);
templateButton.addEventListener("click", loadTemplate);
runButton.addEventListener("click", () => {
  void runSelectedFunction();
});
clearButton.addEventListener("click", clearAll);
fileInput.addEventListener("change", handleFileChange);
var langObserver = new MutationObserver(() => {
  updateHint();
  if (statusBox.textContent === "" || statusBox.textContent === i18n.en.ready || statusBox.textContent === i18n.es.ready) {
    setStatus("info", t("ready"));
  }
});
langObserver.observe(document.documentElement, {
  attributes: true,
  attributeFilter: ["data-current-lang"]
});
updateHint();
autofillTemplateForSelection();
setStatus("info", t("ready"));
