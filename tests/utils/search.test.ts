import { describe, expect, it } from "vitest";
import {
  binarySearchClaimById,
  findClaimById,
  findClinicianById,
} from "../../src/utils/search";
import { sortClaimsById } from "../../src/utils/collections";
import { claims, clinicians } from "./fixtures";

describe("search", () => {
  it("finds a claim by id", () => {
    const result = findClaimById(claims, "CLM-000002");
    expect(result?.payerName).toBe("Aetna");
  });

  it("returns null when claim does not exist", () => {
    expect(findClaimById(claims, "CLM-999999")).toBeNull();
  });

  it("finds a clinician by id", () => {
    const result = findClinicianById(clinicians, "CLN-000003");
    expect(result?.lastName).toBe("Okafor");
  });

  it("performs binary search on sorted claims", () => {
    const sorted = sortClaimsById(claims, "asc");
    const index = binarySearchClaimById(sorted, "CLM-000003");

    expect(index).toBeGreaterThanOrEqual(0);
    expect(sorted[index].claimId).toBe("CLM-000003");
  });

  it("returns -1 when binary search cannot find target", () => {
    const sorted = sortClaimsById(claims, "asc");
    expect(binarySearchClaimById(sorted, "CLM-999999")).toBe(-1);
  });
});