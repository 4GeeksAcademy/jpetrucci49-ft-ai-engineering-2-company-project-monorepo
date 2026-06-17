import type { Claim } from "../entities";

export function findClaimById(claims: Claim[], claimId: string): Claim | null {
  const match = claims.find((claim) => claim.claimId === claimId);
  return match ?? null;
}
