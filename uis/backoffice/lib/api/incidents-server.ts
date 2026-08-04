import { NextResponse } from "next/server";

/** Server-only helpers for proxying incident API requests to FastAPI. */

export const INCIDENTS_API_UNAVAILABLE =
  "Unable to reach the incident analysis API. Ensure it is running (npm run dev:api on port 8000).";

export function getIncidentsApiOrigin(): string {
  return (process.env.INCIDENTS_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
}

export function incidentsApiUnavailableResponse(): NextResponse {
  return NextResponse.json({ detail: INCIDENTS_API_UNAVAILABLE }, { status: 502 });
}

export async function proxyToIncidentsApi(
  path: string,
  init?: RequestInit
): Promise<Response> {
  return fetch(`${getIncidentsApiOrigin()}${path}`, {
    cache: "no-store",
    ...init,
  });
}
