import type { Claim, Clinician } from "../entities";

export function findClaimById(claims: Claim[], claimId: string): Claim | null {
  const match = claims.find((claim) => claim.claimId === claimId);
  return match ?? null;
}

export function findClinicianById(clinicians: Clinician[], clinicianId: string): Clinician | null {
  const match = clinicians.find((clinician) => clinician.clinicianId === clinicianId);
  return match ?? null;
}

export function binarySearchClaimById(sortedClaims: Claim[], targetId: string): number {
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
