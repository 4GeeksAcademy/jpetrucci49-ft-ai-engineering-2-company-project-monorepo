import { NextRequest } from "next/server";

import {
  authApiUnavailableResponse,
  proxyAuthResponse,
  proxyToAuthApi,
} from "@/lib/api/auth-server";

export async function GET(request: NextRequest) {
  try {
    const response = await proxyToAuthApi(request, "/auth/me");
    return proxyAuthResponse(response);
  } catch {
    return authApiUnavailableResponse();
  }
}
