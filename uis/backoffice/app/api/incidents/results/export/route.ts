import { NextResponse } from "next/server";

import {
  incidentsApiUnavailableResponse,
  proxyToIncidentsApi,
} from "@/lib/api/incidents-server";

export async function GET() {
  try {
    const response = await proxyToIncidentsApi("/api/incidents/results/export");
    const body = await response.arrayBuffer();

    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") ?? "text/csv",
        "Content-Disposition":
          response.headers.get("Content-Disposition") ?? 'attachment; filename="results.csv"',
      },
    });
  } catch {
    return incidentsApiUnavailableResponse();
  }
}
