import { describe, expect, it } from "vitest";
import {
  filterAppointmentsByStatus,
  filterClaims,
  groupClaimsBy,
  sortAppointmentsByDate,
  sortClaimsById,
} from "../../src/utils/collections";
import { appointments, claims } from "./fixtures";

describe("collections", () => {
  it("filters claims using all provided filters", () => {
    const result = filterClaims(claims, {
      locationId: "us-tx-001",
      payerName: "BlueCross",
    });

    expect(result).toHaveLength(2);
    expect(result.every((claim) => claim.locationId === "us-tx-001")).toBe(true);
    expect(result.every((claim) => claim.payerName === "BlueCross")).toBe(true);
  });

  it("returns all claims when filters are empty", () => {
    expect(filterClaims(claims, {})).toEqual(claims);
  });

  it("filters appointments by any allowed status", () => {
    const result = filterAppointmentsByStatus(appointments, ["no_show", "scheduled"]);
    expect(result).toHaveLength(3);
  });

  it("returns empty appointments when status filter is empty", () => {
    expect(filterAppointmentsByStatus(appointments, [])).toEqual([]);
  });

  it("sorts claims by id ascending without mutation", () => {
    const unsorted = [claims[2], claims[0], claims[1]];
    const sorted = sortClaimsById(unsorted, "asc");

    expect(sorted.map((claim) => claim.claimId)).toEqual([
      "CLM-000001",
      "CLM-000002",
      "CLM-000003",
    ]);
    expect(unsorted.map((claim) => claim.claimId)).toEqual([
      "CLM-000003",
      "CLM-000001",
      "CLM-000002",
    ]);
  });

  it("sorts appointments by date/time descending", () => {
    const result = sortAppointmentsByDate(appointments, "desc");

    expect(result[0].appointmentId).toBe("APT-000005");
    expect(result.at(-1)?.appointmentId).toBe("APT-000001");
  });

  it("groups claims by payer", () => {
    const grouped = groupClaimsBy(claims, "payerName");

    expect(Object.keys(grouped)).toEqual(["BlueCross", "Aetna", "Medicare", "Cigna"]);
    expect(grouped.BlueCross).toHaveLength(2);
    expect(grouped.Aetna).toHaveLength(1);
    expect(grouped.Medicare).toHaveLength(1);
    expect(grouped.Cigna).toHaveLength(1);
  });
});