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
