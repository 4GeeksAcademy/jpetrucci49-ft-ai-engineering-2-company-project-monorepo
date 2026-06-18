export {};

declare global {
  type AppointmentStatus =
    | "scheduled"
    | "confirmed"
    | "completed"
    | "no_show"
    | "cancelled";

  interface Appointment {
    appointmentId: string;
    patientId: string;
    locationId: string;
    serviceType: ServiceType;
    scheduledDate: string;
    scheduledTime: string;
    status: AppointmentStatus;
    noShowReason?: string;
    confirmedAt?: string;
  }

  type ClaimStatus = "submitted" | "approved" | "denied" | "pending" | "appealed";

  type DenialReason =
    | "missing_authorisation"
    | "coding_error"
    | "duplicate_claim"
    | "patient_not_covered"
    | "service_not_covered"
    | "incomplete_documentation";

  type ServiceType =
    | "primary_care"
    | "chronic_disease"
    | "preventive"
    | "specialist"
    | "womens_health"
    | "paediatric"
    | "mental_health";

  interface Claim {
    claimId: string;
    patientId: string;
    locationId: string;
    serviceType: ServiceType;
    payerName: string;
    payerId: string;
    submissionDate: string;
    claimAmount: number;
    status: ClaimStatus;
    denialReason?: DenialReason;
    resubmitted: boolean;
  }

  type ClinicianRole =
    | "physician"
    | "nurse_practitioner"
    | "nurse"
    | "medical_assistant";

  interface Clinician {
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

  type CMEStatus = "on_track" | "at_risk" | "overdue" | "complete";

  interface CMEReport {
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

  type ConsultantFee = Record<ServiceType, number>;

  interface ClinicLocation {
    locationId: string;
    name: string;
    city: string;
    stateOrCountry: string;
    country: "US" | "UK";
    phone: string;
    averageConsultationFee: ConsultantFee;
  }

  type FilterType = Partial<Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">>;

  interface ValidationResult {
    valid: boolean;
    errors: string[];
  }
}