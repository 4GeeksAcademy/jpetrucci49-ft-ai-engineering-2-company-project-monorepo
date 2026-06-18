import type { Appointment, AppointmentStatus, Claim } from "../entities";

type FilterType = Partial<Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">>;

export function filterClaims(
  claims: Claim[],
  filters: FilterType
): Claim[] {
  return claims.filter((claim) =>
    (Object.keys(filters) as Array<keyof FilterType>).every((filter) => {
      const filterValue = filters[filter];
      if (filterValue === undefined) return true;
      return claim[filter] === filterValue;
    })
  );
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

export function sortAppointmentsByDate(
  appointments: Appointment[],
  direction: "asc" | "desc"
): Appointment[] {
  const sorted = [...appointments].sort((a, b) => {
    const dateCompare = a.scheduledDate.localeCompare(b.scheduledDate);

    if (dateCompare !== 0) return dateCompare;

    return a.scheduledTime.localeCompare(b.scheduledTime);
  });

  return direction === "desc" ? sorted.reverse() : sorted;
}

export function groupClaimsBy(
  claims: Claim[],
  key: "locationId" | "payerName" | "status" | "serviceType"
): Record<string, Claim[]> {
  return claims.reduce<Record<string, Claim[]>>((acc, claim) => {
    const groupKey = claim[key];

    if (!acc[groupKey]) acc[groupKey] = [];

    acc[groupKey].push(claim);
    return acc;
  }, {});
}
