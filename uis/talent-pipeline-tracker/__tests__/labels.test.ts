import { getStageLabel, getStatusLabel } from "@/lib/labels";

describe("getStatusLabel", () => {
  it("returns a friendly label for a known status", () => {
    expect(getStatusLabel("received")).toBe("Received");
  });

  it("returns the raw value for an unknown status", () => {
    expect(getStatusLabel("unknown-status")).toBe("unknown-status");
  });
});

describe("getStageLabel", () => {
  it("returns a friendly label for a known stage", () => {
    expect(getStageLabel("review")).toBe("Under review");
  });

  it("returns the raw value for an unknown stage", () => {
    expect(getStageLabel("mystery-stage")).toBe("mystery-stage");
  });
});
