import type { 
  Appointment,
  Claim,
  Clinician,
  CMEReport,
  CMEStatus,
  Location,
} from "../entities";

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

const daysBetween = (start: Date, end: Date): number => {
  const msPerDay = 24 * 60 * 60 * 1000;
  return Math.floor((end.getTime() - start.getTime()) / msPerDay);
}

const getCycleEndDate = (cmeYearStartDate: string): Date => {
  const cycleStart = toUtcDate(cmeYearStartDate);
  const cycleEnd = new Date(cycleStart.getTime());
  cycleEnd.setUTCFullYear(cycleEnd.getUTCFullYear() + 1);
  cycleEnd.setUTCDate(cycleEnd.getUTCDate() - 1);
  return cycleEnd;
}

const getComplianceStatus = (clinician: Clinician, asOfDate: Date): CMEStatus => {
  const cycleStart = toUtcDate(clinician.cmeYearStartDate);
  const cycleEnd = getCycleEndDate(clinician.cmeYearStartDate);

  if (clinician.cmeHoursLogged >= clinician.cmeHoursRequired) return "complete";

  if (asOfDate.getTime() > cycleEnd.getTime() && clinician.cmeHoursLogged < clinician.cmeHoursRequired) return "overdue";

  const totalCycleDays = Math.max(1, daysBetween(cycleStart, cycleEnd) + 1);
  const elapsedDays = Math.min(Math.max(daysBetween(cycleStart, asOfDate) + 1, 0), totalCycleDays);
  const elapsedPercent = (elapsedDays / totalCycleDays) * 100;

  const percentComplete =
    clinician.cmeHoursRequired === 0
      ? 100
      : (clinician.cmeHoursLogged / clinician.cmeHoursRequired) * 100;

  if (percentComplete < elapsedPercent - 15) return "at_risk";

  return "on_track";
}

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

export function generateCMEReport(clinicians: Clinician[], asOfDate: string): CMEReport[] {
  const asOf = toUtcDate(asOfDate);
  if (!isValidDate(asOf)) {
    throw new Error("asOfDate must be a valid ISO date string.");
  }

  return clinicians.map((clinician) => {
    const hoursRemaining = Math.max(0, clinician.cmeHoursRequired - clinician.cmeHoursLogged);
    const percentComplete =
      clinician.cmeHoursRequired === 0
        ? 100
        : roundTo((clinician.cmeHoursLogged / clinician.cmeHoursRequired) * 100, 1);

    const cycleEnd = getCycleEndDate(clinician.cmeYearStartDate);
    const daysRemainingInCycle = daysBetween(asOf, cycleEnd);

    const licenceExpiry = toUtcDate(clinician.licenceExpiryDate);
    const licenceDaysRemaining = daysBetween(asOf, licenceExpiry);

    return {
      clinicianId: clinician.clinicianId,
      fullName: `${clinician.firstName} ${clinician.lastName}`,
      role: clinician.role,
      locationId: clinician.locationId,
      hoursRequired: clinician.cmeHoursRequired,
      hoursLogged: clinician.cmeHoursLogged,
      hoursRemaining,
      percentComplete,
      daysRemainingInCycle,
      complianceStatus: getComplianceStatus(clinician, asOf),
      licenceExpiryDate: clinician.licenceExpiryDate,
      licenceDaysRemaining,
    };
  });
}

export function getCliniciansAtRisk(clinicians: Clinician[], asOfDate: string): Clinician[] {
  const report = generateCMEReport(clinicians, asOfDate);
  const atRiskIds = new Set(
    report
      .filter((item) => item.complianceStatus === "at_risk" || item.complianceStatus === "overdue")
      .map((item) => item.clinicianId)
  );

  return clinicians.filter((clinician) => atRiskIds.has(clinician.clinicianId));
}
