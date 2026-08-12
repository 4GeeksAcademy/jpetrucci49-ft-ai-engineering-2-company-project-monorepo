import { NextRequest, NextResponse } from "next/server";

import {
  incidentsApiUnavailableResponse,
  proxyToIncidentsApi,
} from "@/lib/api/incidents-server";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const response = await proxyToIncidentsApi(request, "/api/incidents/analyze", {
      method: "POST",
      body: formData,
    });

    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") ?? "application/json",
      },
    });
  } catch {
    return incidentsApiUnavailableResponse();
  }
}
