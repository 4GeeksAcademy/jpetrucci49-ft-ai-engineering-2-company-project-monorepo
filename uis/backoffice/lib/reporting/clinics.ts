/** Reporting slugs → labels. Matches PIPELINE_DESIGN.md §4.2. */

export const REPORTING_CLINIC_LABELS: Record<string, string> = {
  "austin-main": "Austin Main",
  "austin-north": "Austin North",
  "dallas-uptown": "Dallas Uptown",
  "houston-medical-center": "Houston Medical Center",
  "san-antonio-west": "San Antonio West",
  "miami-brickell": "Miami Brickell",
  "orlando-east": "Orlando East",
  "tampa-bay": "Tampa Bay",
  "atlanta-midtown": "Atlanta Midtown",
  "london-city": "London City",
  "london-west": "London West",
  "manchester-central": "Manchester Central",
};

export const COUNTRY_LABELS: Record<string, string> = {
  US: "United States",
  UK: "United Kingdom",
};

export function clinicLabel(clinicId: string): string {
  return REPORTING_CLINIC_LABELS[clinicId] ?? clinicId;
}

export function countryLabel(country: string): string {
  return COUNTRY_LABELS[country] ?? country;
}

export function formatMonthPeriod(monthStart: string | null): { heading: string; starting: string } {
  if (!monthStart) {
    return { heading: "No month computed yet", starting: "" };
  }
  const [year, month] = monthStart.split("-").map(Number);
  const heading = new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
  return { heading, starting: `Month starting ${monthStart}` };
}
