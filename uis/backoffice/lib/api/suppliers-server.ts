import { NextResponse } from "next/server";

/** Server-only helpers for proxying supplier API requests to FastAPI. */

export const SUPPLIERS_API_UNAVAILABLE =
  "Unable to reach the supplier directory API. Ensure it is running (npm run dev:api on port 8000).";

export function getSuppliersApiOrigin(): string {
  return (process.env.SUPPLIERS_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
}

export function suppliersApiUnavailableResponse(): NextResponse {
  return NextResponse.json({ detail: SUPPLIERS_API_UNAVAILABLE }, { status: 502 });
}

export async function proxyToSuppliersApi(
  path: string,
  init?: RequestInit
): Promise<Response> {
  return fetch(`${getSuppliersApiOrigin()}${path}`, {
    cache: "no-store",
    ...init,
  });
}

export async function proxySuppliersResponse(response: Response): Promise<NextResponse> {
  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json",
    },
  });
}
