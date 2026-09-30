import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { forwardAuthorization } from "@healthcore/api/proxy";
import { proxySanitizedResponse, runBffHandler } from "@/lib/api/bff-proxy";

export const RFP_API_UNAVAILABLE =
  "Unable to reach the RFP intake API. Ensure it is running (npm run dev:api on port 8000).";

export function getRfpApiOrigin(): string {
  return (process.env.INVENTORY_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
}

export function rfpApiUnavailableResponse(): NextResponse {
  return NextResponse.json({ detail: RFP_API_UNAVAILABLE }, { status: 502 });
}

export async function proxyToRfpApi(
  request: NextRequest,
  path: string,
  init?: RequestInit
): Promise<Response> {
  const headers = forwardAuthorization(request.headers.get("authorization"), init?.headers);
  return fetch(`${getRfpApiOrigin()}${path}`, {
    cache: "no-store",
    ...init,
    headers,
  });
}

export function proxyRfpResponse(response: Response): Promise<NextResponse> {
  return proxySanitizedResponse(response);
}

export function runRfpBffHandler(handler: () => Promise<NextResponse>): Promise<NextResponse> {
  return runBffHandler(rfpApiUnavailableResponse, handler);
}
