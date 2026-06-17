import type { Appointment, Claim, Location } from "../entities";

const roundTo = (value: number, decimals: number): number => {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

const calculateRate = (total: number, matching: number): number => (
  total === 0 ? 0 : roundTo((matching / total) * 100, 2)
);

const toUtcDate = (dateString: string): Date => (
  new Date(`${dateString}T00:00:00.000Z`)
);

const isValidDate = (date: Date): boolean => (
  !Number.isNaN(date.getTime())
);

export function calculateDenialRate(claims: Claim[]): number {
  if (claims.length === 0) {
    throw new Error("Cannot calculate denial rate for an empty claims array.");
  }

  const deniedCount = claims.filter((claim) => claim.status === "denied").length;
  return calculateRate(claims.length, deniedCount);
}

export function denialRateByPayer(claims: Claim[]): Record<string, number> {
  const groups = claims.reduce<Record<string, Claim[]>>((acc, claim) => {
    if (!acc[claim.payerName]) acc[claim.payerName] = [];

    acc[claim.payerName].push(claim);
    return acc;
  }, {});

  return Object.fromEntries(
    Object.entries(groups).map(([payerName, payerClaims]) => {
      const deniedCount = payerClaims.filter((claim) => claim.status === "denied").length;
      return [payerName, calculateRate(payerClaims.length, deniedCount)];
    })
  );
}

export function denialRateByLocation(claims: Claim[]): Record<string, number> {
  const groups = claims.reduce<Record<string, Claim[]>>((acc, claim) => {
    if (!acc[claim.locationId]) acc[claim.locationId] = [];

    acc[claim.locationId].push(claim);
    return acc;
  }, {});

  return Object.fromEntries(
    Object.entries(groups).map(([locationId, locationClaims]) => {
      const deniedCount = locationClaims.filter((claim) => claim.status === "denied").length;
      return [locationId, calculateRate(locationClaims.length, deniedCount)];
    })
  );
}

export function flagHighDenialPayers(claims: Claim[], threshold: number = 8): string[] {
  const byPayer = denialRateByPayer(claims);

  return Object.entries(byPayer)
    .filter(([, rate]) => rate > threshold)
    .map(([payer]) => payer);
}

export function calculateNoShowCost(
  appointments: Appointment[],
  location: Location,
  weekEndingDate: string
): number {
  const endDate = toUtcDate(weekEndingDate);
  if (!isValidDate(endDate)) {
    throw new Error("weekEndingDate must be a valid ISO date string.");
  }

  const startDate = new Date(endDate.getTime());
  startDate.setUTCDate(startDate.getUTCDate() - 6);

  const total = appointments
    .filter((appointment) => {
      if (appointment.locationId !== location.locationId) return false;

      if (appointment.status !== "no_show") return false;

      const appointmentDate = toUtcDate(appointment.scheduledDate);
      return appointmentDate.getTime() >= startDate.getTime() && appointmentDate.getTime() <= endDate.getTime();
    })
    .reduce((sum, appointment) => {
      return sum + location.averageConsultationFee[appointment.serviceType];
    }, 0);

  return roundTo(total, 2);
}

export function noShowRateByLocation(appointments: Appointment[]): Record<string, number> {
  const groups = appointments.reduce<Record<string, Appointment[]>>((acc, appointment) => {
    if (!acc[appointment.locationId]) acc[appointment.locationId] = [];

    acc[appointment.locationId].push(appointment);
    return acc;
  }, {});

  return Object.fromEntries(
    Object.entries(groups).map(([locationId, locationAppointments]) => {
      const noShowCount = locationAppointments.filter((appointment) => appointment.status === "no_show").length;
      return [locationId, calculateRate(locationAppointments.length, noShowCount)];
    })
  );
}

export function flagHighNoShowLocations(
  appointments: Appointment[],
  threshold: number = 20
): string[] {
  const rates = noShowRateByLocation(appointments);

  return Object.entries(rates)
    .filter(([, rate]) => rate > threshold)
    .map(([locationId]) => locationId);
}
