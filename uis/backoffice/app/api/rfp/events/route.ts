import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { proxyRfpResponse, proxyToRfpApi, runRfpBffHandler } from "@/lib/api/rfp-server";

export const dynamic = "force-dynamic";

const STREAM_HEADERS = {
  "Content-Type": "text/event-stream",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
  "X-Accel-Buffering": "no",
};

export async function GET(request: NextRequest) {
  return runRfpBffHandler(async () => {
    const response = await proxyToRfpApi(request, "/rfp/events", {
      method: "GET",
      headers: { Accept: "text/event-stream" },
    });
    if (!response.ok || response.body === null) {
      return proxyRfpResponse(response);
    }
    return new NextResponse(response.body, {
      status: response.status,
      headers: STREAM_HEADERS,
    });
  });
}
