import type { ClinicianRole } from "./clinician";

export type CMEStatus = "on_track" | "at_risk" | "overdue" | "complete";

export interface CMEReport {
  clinicianId: string;
  fullName: string;
  role: ClinicianRole;
  locationId: string;
  hoursRequired: number;
  hoursLogged: number;
  hoursRemaining: number;
  percentComplete: number;
  daysRemainingInCycle: number;
  complianceStatus: CMEStatus;
  licenceExpiryDate: string;
  licenceDaysRemaining: number;
}