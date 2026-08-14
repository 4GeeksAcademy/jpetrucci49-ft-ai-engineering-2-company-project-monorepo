import { NextRequest } from "next/server";

import {
  authApiUnavailableResponse,
  proxyAuthResponse,
  proxyToAuthApi,
} from "@/lib/api/auth-server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const response = await proxyToAuthApi(request, "/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return proxyAuthResponse(response);
  } catch {
    return authApiUnavailableResponse();
  }
}
