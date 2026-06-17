import type { Appointment, AppointmentStatus, Claim } from "../entities";

type FilterType = Partial<Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">>;

export function filterClaims(
  claims: Claim[],
  filters: FilterType
): Claim[] {
  return claims.filter((claim) => (
    (Object.keys(filters) as Array<keyof FilterType>).every(
      filter => filters[filter] !== undefined && claim[filter] !== filters[filter]
    )
        ? false
        : true
  ));
}

export function filterAppointmentsByStatus(
  appointments: Appointment[],
  status: AppointmentStatus[]
): Appointment[] {
  if (status.length === 0) return [];

  const allowed = new Set(status);
  return appointments.filter((appointment) => allowed.has(appointment.status));
}

export function sortClaimsById(claims: Claim[], direction: "asc" | "desc"): Claim[] {
  const sorted = [...claims].sort((a, b) => a.claimId.localeCompare(b.claimId));
  return direction === "desc" ? sorted.reverse() : sorted;
}
