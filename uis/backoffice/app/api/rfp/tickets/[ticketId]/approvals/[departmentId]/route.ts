import { NextRequest, NextResponse } from "next/server";

import { proxyRfpResponse, proxyToRfpApi, runRfpBffHandler } from "@/lib/api/rfp-server";

type RouteContext = { params: Promise<{ ticketId: string; departmentId: string }> };

export async function POST(request: NextRequest, context: RouteContext) {
  return runRfpBffHandler(async () => {
    const { ticketId, departmentId } = await context.params;
    if (!ticketId || !departmentId) {
      return NextResponse.json({ detail: "Ticket not found." }, { status: 404 });
    }
    const body = await request.text();
    const response = await proxyToRfpApi(
      request,
      `/rfp/tickets/${ticketId}/approvals/${departmentId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      },
    );
    return proxyRfpResponse(response);
  });
}
