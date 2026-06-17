export type ClinicianRole =
  | "physician"
  | "nurse_practitioner"
  | "nurse"
  | "medical_assistant";

export interface Clinician {
  clinicianId: string;
  firstName: string;
  lastName: string;
  role: ClinicianRole;
  locationId: string;
  licenceState: string;
  licenceExpiryDate: string;
  cmeHoursRequired: number;
  cmeHoursLogged: number;
  cmeYearStartDate: string;
}