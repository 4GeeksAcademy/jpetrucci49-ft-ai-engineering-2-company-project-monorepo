import { NextRequest, NextResponse } from "next/server";

import { forwardAuthorization, getFastApiOrigin } from "@healthcore/api/proxy";

export const AUTH_API_UNAVAILABLE =
  "Unable to reach the authentication API. Ensure it is running (npm run dev:api on port 8000).";

export function authApiUnavailableResponse(): NextResponse {
  return NextResponse.json({ detail: AUTH_API_UNAVAILABLE }, { status: 502 });
}

export async function proxyAuthResponse(response: Response): Promise<NextResponse> {
  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json",
    },
  });
}

export async function proxyToAuthApi(
  request: NextRequest,
  path: string,
  init?: RequestInit
): Promise<Response> {
  const headers = forwardAuthorization(request.headers.get("authorization"), init?.headers);
  return fetch(`${getFastApiOrigin()}${path}`, {
    cache: "no-store",
    ...init,
    headers,
  });
}
