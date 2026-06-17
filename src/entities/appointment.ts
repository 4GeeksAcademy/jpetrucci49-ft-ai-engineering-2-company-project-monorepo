import type { ServiceType } from "./claim";

export type AppointmentStatus =
  | "scheduled"
  | "confirmed"
  | "completed"
  | "no_show"
  | "cancelled";

export interface Appointment {
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