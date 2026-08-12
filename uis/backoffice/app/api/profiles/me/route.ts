import { NextRequest } from "next/server";

import {
  authApiUnavailableResponse,
  proxyAuthResponse,
  proxyToAuthApi,
} from "@/lib/api/auth-server";

export async function PUT(request: NextRequest) {
  try {
    const body = await request.text();
    const response = await proxyToAuthApi(request, "/profiles/me", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return proxyAuthResponse(response);
  } catch {
    return authApiUnavailableResponse();
  }
}
