import { NextRequest } from "next/server";

import { proxyRfpResponse, proxyToRfpApi, runRfpBffHandler } from "@/lib/api/rfp-server";

export async function GET(request: NextRequest) {
  return runRfpBffHandler(async () => {
    const response = await proxyToRfpApi(request, "/rfp/tickets", { method: "GET" });
    return proxyRfpResponse(response);
  });
}

export async function POST(request: NextRequest) {
  return runRfpBffHandler(async () => {
    const formData = await request.formData();
    const response = await proxyToRfpApi(request, "/rfp/tickets", {
      method: "POST",
      body: formData,
    });
    return proxyRfpResponse(response);
  });
}
