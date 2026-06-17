import type { Claim } from "../entities";

const roundTo = (value: number, decimals: number): number => {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

const calculateRate = (total: number, matching: number): number => (
  total === 0 ? 0 : roundTo((matching / total) * 100, 2)
);

export function calculateDenialRate(claims: Claim[]): number {
  if (claims.length === 0) {
    throw new Error("Cannot calculate denial rate for an empty claims array.");
  }

  const deniedCount = claims.filter((claim) => claim.status === "denied").length;
  return calculateRate(claims.length, deniedCount);
}

export function denialRateByPayer(claims: Claim[]): Record<string, number> {
  const groups = claims.reduce<Record<string, Claim[]>>((acc, claim) => {
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

export function denialRateByLocation(claims: Claim[]): Record<string, number> {
  const groups = claims.reduce<Record<string, Claim[]>>((acc, claim) => {
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
