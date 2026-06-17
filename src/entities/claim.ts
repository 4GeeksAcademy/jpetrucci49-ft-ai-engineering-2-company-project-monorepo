export type ClaimStatus = "submitted" | "approved" | "denied" | "pending" | "appealed";

export type DenialReason =
  | "missing_authorisation"
  | "coding_error"
  | "duplicate_claim"
  | "patient_not_covered"
  | "service_not_covered"
  | "incomplete_documentation";

export type ServiceType =
  | "primary_care"
  | "chronic_disease"
  | "preventive"
  | "specialist"
  | "womens_health"
  | "paediatric"
  | "mental_health";

export interface Claim {
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