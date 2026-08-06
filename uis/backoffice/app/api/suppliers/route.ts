import { NextRequest } from "next/server";

import {
  proxySuppliersResponse,
  proxyToSuppliersApi,
  suppliersApiUnavailableResponse,
} from "@/lib/api/suppliers-server";

export async function GET(request: NextRequest) {
  try {
    const search = request.nextUrl.searchParams.toString();
    const path = search ? `/suppliers?${search}` : "/suppliers";
    const response = await proxyToSuppliersApi(path);
    return proxySuppliersResponse(response);
  } catch {
    return suppliersApiUnavailableResponse();
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const response = await proxyToSuppliersApi("/suppliers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return proxySuppliersResponse(response);
  } catch {
    return suppliersApiUnavailableResponse();
  }
}
