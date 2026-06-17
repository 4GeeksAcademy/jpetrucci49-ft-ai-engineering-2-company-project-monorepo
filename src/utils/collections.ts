import type { Claim } from "../entities";

export function filterClaims(
  claims: Claim[],
  filters: Partial<Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">>
): Claim[] {
  return claims.filter((claim) => {
    if (filters.locationId !== undefined && claim.locationId !== filters.locationId) {
      return false;
    }

    if (filters.status !== undefined && claim.status !== filters.status) {
      return false;
    }

    if (filters.payerName !== undefined && claim.payerName !== filters.payerName) {
      return false;
    }

    if (filters.serviceType !== undefined && claim.serviceType !== filters.serviceType) {
      return false;
    }

    return true;
  });
}
