import { NextRequest, NextResponse } from "next/server";

import { proxyRfpResponse, proxyToRfpApi, runRfpBffHandler } from "@/lib/api/rfp-server";

type RouteContext = { params: Promise<{ ticketId: string }> };

export async function GET(request: NextRequest, context: RouteContext) {
  return runRfpBffHandler(async () => {
    const { ticketId } = await context.params;
    if (!ticketId) {
      return NextResponse.json({ detail: "Ticket not found." }, { status: 404 });
    }
    const response = await proxyToRfpApi(request, `/rfp/tickets/${ticketId}`);
    return proxyRfpResponse(response);
  });
}
