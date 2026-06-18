import { describe, expect, it } from "vitest";
import {
  calculateDenialRate,
  calculateNoShowCost,
  denialRateByLocation,
  denialRateByPayer,
  flagHighDenialPayers,
  flagHighNoShowLocations,
  generateCMEReport,
  getCliniciansAtRisk,
  getCliniciansWithExpiringLicences,
  noShowRateByLocation,
} from "../../src/utils/transformations";
import { appointments, claims, clinicians, locations } from "./fixtures";

describe("transformations", () => {
  it("calculates denial rate with 2 decimals", () => {
    expect(calculateDenialRate(claims)).toBe(40);
  });

  it("throws when calculating denial rate with empty claims", () => {
    expect(() => calculateDenialRate([])).toThrowError();
  });

  it("computes denial rates by payer", () => {
    expect(denialRateByPayer(claims)).toEqual({
      BlueCross: 50,
      Aetna: 100,
      Medicare: 0,
      Cigna: 0,
    });
  });

  it("computes denial rates by location", () => {
    expect(denialRateByLocation(claims)).toEqual({
      "us-tx-001": 50,
      "us-fl-001": 50,
      "us-ga-001": 0,
    });
  });

  it("flags payers with denial rates above threshold", () => {
    expect(flagHighDenialPayers(claims, 40)).toEqual(["BlueCross", "Aetna"]);
    expect(flagHighDenialPayers(claims, 60)).toEqual(["Aetna"]);
  });

  it("calculates weekly no-show cost per location", () => {
    const cost = calculateNoShowCost(appointments, locations[0], "2025-03-12");
    expect(cost).toBe(220);
  });

  it("computes no-show rates by location", () => {
    expect(noShowRateByLocation(appointments)).toEqual({
      "us-tx-001": 50,
      "us-fl-001": 100,
      "us-ga-001": 0,
    });
  });

  it("flags locations above no-show threshold", () => {
    expect(flagHighNoShowLocations(appointments, 70)).toEqual(["us-fl-001"]);
  });

  it("generates CME report with expected statuses", () => {
    const report = generateCMEReport(clinicians, "2025-06-15");

    expect(report).toHaveLength(3);
    expect(report.find((item) => item.clinicianId === "CLN-000001")?.complianceStatus).toBe("on_track");
    expect(report.find((item) => item.clinicianId === "CLN-000002")?.complianceStatus).toBe("at_risk");
    expect(report.find((item) => item.clinicianId === "CLN-000003")?.complianceStatus).toBe("complete");
  });

  it("returns clinicians at risk or overdue", () => {
    const result = getCliniciansAtRisk(clinicians, "2025-12-15");
    expect(result.map((clinician) => clinician.clinicianId)).toEqual(["CLN-000001", "CLN-000002"]);
  });

  it("returns clinicians with expiring licences within threshold", () => {
    const result = getCliniciansWithExpiringLicences(clinicians, "2025-06-15", 30);
    expect(result.map((clinician) => clinician.clinicianId)).toEqual([]);
  });
});