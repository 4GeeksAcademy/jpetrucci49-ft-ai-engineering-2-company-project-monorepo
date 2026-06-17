import type { Claim } from "../entities";

type FilterType = Partial<Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">>;

export function filterClaims(
  claims: Claim[],
  filters: FilterType
): Claim[] {
  return claims.filter((claim) => (
    (Object.keys(filters) as Array<keyof FilterType>).every(
      filter => filters[filter] !== undefined && claim[filter] !== filters[filter]
    )
        ? false
        : true
  ));
}
