const isValidDateString = (dateString: string): boolean => {
  const date = new Date(`${dateString}T00:00:00.000Z`);
  return !Number.isNaN(date.getTime());
}

const isFutureDate = (dateString: string): boolean => {
  const now = new Date();
  const todayUtc = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const date = new Date(`${dateString}T00:00:00.000Z`);
  return date.getTime() > todayUtc.getTime();
}

export function validateClaim(claim: Claim, knownLocationIds: string[]): ValidationResult {
  const errors: string[] = [];

  if (claim.claimAmount <= 0) errors.push("claimAmount must be greater than 0.");

  if (!isValidDateString(claim.submissionDate)) errors.push("submissionDate must be a valid ISO 8601 date string.");
  else if (isFutureDate(claim.submissionDate)) errors.push("submissionDate must not be a future date.");

  if (!knownLocationIds.includes(claim.locationId)) errors.push("locationId must match a known clinic ID.");

  if (claim.status === "denied" && !claim.denialReason) errors.push("denialReason is required when status is denied.");

  if (!/^HC-[A-Za-z0-9]{6}$/.test(claim.patientId)) errors.push("patientId must match the format HC- followed by 6 alphanumeric characters.");

  return {
    valid: errors.length === 0,
    errors,
  };
}

export function validateClinician(clinician: Clinician): ValidationResult {
  const errors: string[] = [];

  if (clinician.cmeHoursRequired < 0) errors.push("cmeHoursRequired must be greater than or equal to 0.");

  if (clinician.cmeHoursLogged < 0) errors.push("cmeHoursLogged must be greater than or equal to 0.");

  const allowedRoles = new Set(["physician", "nurse_practitioner", "nurse", "medical_assistant"]);
  if (!allowedRoles.has(clinician.role)) errors.push("role must be one of: physician, nurse_practitioner, nurse, medical_assistant.");

  if (!isValidDateString(clinician.licenceExpiryDate)) errors.push("licenceExpiryDate must be a valid ISO 8601 date string.");
  else {
    const now = new Date();
    const todayUtc = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
    const expiryDate = new Date(`${clinician.licenceExpiryDate}T00:00:00.000Z`);

    if (expiryDate.getTime() < todayUtc.getTime()) errors.push("licenceExpiryDate is expired.");
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

export function isDenialRateAboveThreshold(rate: number, threshold: number = 8): boolean {
  return rate > threshold;
}

export function isNoShowRateAboveThreshold(rate: number, threshold: number = 20): boolean {
  return rate > threshold;
}