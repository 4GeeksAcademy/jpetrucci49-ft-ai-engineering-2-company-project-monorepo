import { NextRequest, NextResponse } from "next/server";

import {
  proxySuppliersResponse,
  proxyToSuppliersApi,
  suppliersApiUnavailableResponse,
} from "@/lib/api/suppliers-server";

type RouteContext = { params: Promise<{ id: string }> };

export async function DELETE(_request: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    const response = await proxyToSuppliersApi(`/suppliers/${id}`, { method: "DELETE" });

    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    return proxySuppliersResponse(response);
  } catch {
    return suppliersApiUnavailableResponse();
  }
}
