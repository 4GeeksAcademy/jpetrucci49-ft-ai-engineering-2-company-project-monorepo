import type { RecordCreate } from "@/types/record";

export type RecordFormValues = RecordCreate;

export interface FieldErrors {
  full_name?: string;
  email?: string;
  phone?: string;
  position?: string;
  experience_years?: string;
  linkedin_url?: string;
  cv_url?: string;
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateRecordForm(values: RecordFormValues): FieldErrors {
  const errors: FieldErrors = {};

  if (!values.full_name.trim()) {
    errors.full_name = "Full name is required.";
  }

  if (!values.email.trim()) {
    errors.email = "Email is required.";
  } else if (!EMAIL_PATTERN.test(values.email.trim())) {
    errors.email = "Enter a valid email address.";
  }

  if (!values.phone.trim()) {
    errors.phone = "Phone is required.";
  }

  if (!values.position.trim()) {
    errors.position = "Position is required.";
  }

  if (Number.isNaN(values.experience_years) || values.experience_years < 0) {
    errors.experience_years = "Years of experience must be zero or greater.";
  }

  return errors;
}

export function hasFieldErrors(errors: FieldErrors): boolean {
  return Object.keys(errors).length > 0;
}

export function validateNoteContent(content: string): string | null {
  if (!content.trim()) return "Note content is required.";
  return null;
}
