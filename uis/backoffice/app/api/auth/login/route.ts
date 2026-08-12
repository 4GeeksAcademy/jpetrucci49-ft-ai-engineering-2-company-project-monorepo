import { NextRequest } from "next/server";

import {
  authApiUnavailableResponse,
  proxyAuthResponse,
} from "@/lib/api/auth-server";
import { getFastApiOrigin } from "@healthcore/api/proxy";

export async function POST(request: NextRequest) {
  try {
    const { email, password } = (await request.json()) as { email: string; password: string };
    const body = new URLSearchParams({
      username: email,
      password,
    });

    const response = await fetch(`${getFastApiOrigin()}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
      cache: "no-store",
    });

    return proxyAuthResponse(response);
  } catch {
    return authApiUnavailableResponse();
  }
}
