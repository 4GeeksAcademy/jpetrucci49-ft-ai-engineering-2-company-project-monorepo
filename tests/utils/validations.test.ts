import { describe, expect, it } from "vitest";
import {
  isDenialRateAboveThreshold,
  isNoShowRateAboveThreshold,
  validateClaim,
  validateClinician,
} from "../../src/utils/validations";
import { claims, clinicians } from "./fixtures";

const addDays = (base: Date, days: number): string => {
  const date = new Date(base.getTime());
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
};

describe("validations", () => {
  it("validates a correct claim", () => {
    const result = validateClaim(claims[0], ["us-tx-001", "us-fl-001", "us-ga-001"]);
    expect(result).toEqual({ valid: true, errors: [] });
  });

  it("returns multiple errors for an invalid claim", () => {
    const result = validateClaim(
      {
        ...claims[0],
        claimAmount: 0,
        locationId: "unknown",
        patientId: "bad-id",
        status: "denied",
        denialReason: undefined,
      },
      ["us-tx-001"]
    );

    expect(result.valid).toBe(false);
    expect(result.errors.length).toBeGreaterThanOrEqual(4);
  });

  it("validates a clinician with a future licence date", () => {
    const baseNow = new Date();
    const result = validateClinician({
      ...clinicians[0],
      licenceExpiryDate: addDays(baseNow, 7),
    });

    expect(result.valid).toBe(true);
  });

  it("flags an expired clinician licence", () => {
    const baseNow = new Date();
    const result = validateClinician({
      ...clinicians[0],
      licenceExpiryDate: addDays(baseNow, -7),
    });

    expect(result.valid).toBe(false);
    expect(result.errors).toContain("licenceExpiryDate is expired.");
  });

  it("checks denial threshold with default and custom values", () => {
    expect(isDenialRateAboveThreshold(9)).toBe(true);
    expect(isDenialRateAboveThreshold(9, 10)).toBe(false);
  });

  it("checks no-show threshold with default and custom values", () => {
    expect(isNoShowRateAboveThreshold(21)).toBe(true);
    expect(isNoShowRateAboveThreshold(21, 30)).toBe(false);
  });
});