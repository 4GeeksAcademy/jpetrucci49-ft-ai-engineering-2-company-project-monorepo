import type { Claim, Clinician } from "../entities";

export function findClaimById(claims: Claim[], claimId: string): Claim | null {
  const match = claims.find((claim) => claim.claimId === claimId);
  return match ?? null;
}

export function findClinicianById(clinicians: Clinician[], clinicianId: string): Clinician | null {
  const match = clinicians.find((clinician) => clinician.clinicianId === clinicianId);
  return match ?? null;
}
