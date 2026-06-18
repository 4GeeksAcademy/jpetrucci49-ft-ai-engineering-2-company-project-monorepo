import type { Claim } from "../entities";

interface ValidationResult {
  valid: boolean;
  errors: string[];
}

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
