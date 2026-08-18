import {
  hasFieldErrors,
  validateNoteContent,
  validateRecordForm,
} from "@/lib/validation";
import type { RecordFormValues } from "@/lib/validation";

const validRecord: RecordFormValues = {
  full_name: "Jane Candidate",
  email: "jane@example.com",
  phone: "+1 555-0100",
  position: "Registered Nurse",
  experience_years: 5,
  linkedin_url: "",
  cv_url: "",
};

describe("validateRecordForm", () => {
  it("returns no errors for a complete valid payload", () => {
    expect(validateRecordForm(validRecord)).toEqual({});
  });

  it("flags a missing email", () => {
    const errors = validateRecordForm({ ...validRecord, email: "" });
    expect(errors.email).toBe("Email is required.");
  });
});

describe("hasFieldErrors", () => {
  it("returns false when there are no errors", () => {
    expect(hasFieldErrors({})).toBe(false);
  });

  it("returns true when any field error is present", () => {
    expect(hasFieldErrors({ email: "Email is required." })).toBe(true);
  });
});

describe("validateNoteContent", () => {
  it("accepts non-empty trimmed content", () => {
    expect(validateNoteContent("Follow-up scheduled.")).toBeNull();
  });

  it("rejects whitespace-only content", () => {
    expect(validateNoteContent("   ")).toBe("Note content is required.");
  });
});
