import type { Claim } from "../entities";

export function filterClaims(
  claims: Claim[],
  filters: Partial<Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">>
): Claim[] {
  return claims.filter((claim) => (filters.locationId !== undefined && claim.locationId !== filters.locationId)
      || (filters.status !== undefined && claim.status !== filters.status)
      || (filters.payerName !== undefined && claim.payerName !== filters.payerName)
      || (filters.serviceType !== undefined && claim.serviceType !== filters.serviceType) 
        ? false
        : true
  );
}
