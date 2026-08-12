import { NextRequest } from "next/server";

import {
  proxySuppliersResponse,
  proxyToSuppliersApi,
  suppliersApiUnavailableResponse,
} from "@/lib/api/suppliers-server";

type RouteContext = { params: Promise<{ id: string }> };

export async function PATCH(request: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    const body = await request.text();
    const response = await proxyToSuppliersApi(request, `/suppliers/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return proxySuppliersResponse(response);
  } catch {
    return suppliersApiUnavailableResponse();
  }
}
