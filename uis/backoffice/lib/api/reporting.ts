import { authFetch, parseApiError } from "@healthcore/auth";
import { toUserFacingMessage } from "@healthcore/api/errors";

const NETWORK_ERROR = "Unable to reach the server. Check your connection and try again.";
const INVALID_RESPONSE = "Received an invalid response from the server.";
const SERVER_ERROR = "An unexpected error occurred.";

export class ReportingApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ReportingApiError";
    this.status = status;
  }
}

export type ClinicSupplyPerformance = {
  clinic_id: string;
  country: string;
  total_supply_cost: number;
  supply_consumption_count: number;
  critical_stockout_count: number;
  expiry_risk_count: number;
  currency: string;
};

export type MonthlyClinicSupplyPerformance = {
  month_start: string | null;
  clinics: ClinicSupplyPerformance[];
};

export type PipelineRunLatest = {
  id: string;
  pipeline_name: string;
  month_start: string | null;
  started_at: string | null;
  finished_at: string | null;
  status: string;
  records_read: number;
  records_written: number;
  error_message: string | null;
};

async function requestJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await authFetch(path);
  } catch (error) {
    throw new ReportingApiError(toUserFacingMessage(error, NETWORK_ERROR), 0);
  }

  if (!response.ok) {
    const raw = await parseApiError(response);
    const message =
      response.status >= 500 ? toUserFacingMessage(new Error(raw), SERVER_ERROR, response.status) : raw;
    throw new ReportingApiError(message, response.status);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ReportingApiError(INVALID_RESPONSE, response.status);
  }
}

export async function fetchMonthlyClinicSupplyPerformance(
  monthStart?: string
): Promise<MonthlyClinicSupplyPerformance> {
  const search = new URLSearchParams();
  if (monthStart) search.set("month_start", monthStart);
  const query = search.toString();
  return requestJson<MonthlyClinicSupplyPerformance>(
    `/api/reporting/monthly-clinic-supply-performance${query ? `?${query}` : ""}`
  );
}

export async function fetchLatestPipelineRun(): Promise<PipelineRunLatest | null> {
  let response: Response;
  try {
    response = await authFetch("/api/reporting/pipeline-runs/latest");
  } catch (error) {
    throw new ReportingApiError(toUserFacingMessage(error, NETWORK_ERROR), 0);
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    const raw = await parseApiError(response);
    const message =
      response.status >= 500 ? toUserFacingMessage(new Error(raw), SERVER_ERROR, response.status) : raw;
    throw new ReportingApiError(message, response.status);
  }

  try {
    return (await response.json()) as PipelineRunLatest;
  } catch {
    throw new ReportingApiError(INVALID_RESPONSE, response.status);
  }
}
