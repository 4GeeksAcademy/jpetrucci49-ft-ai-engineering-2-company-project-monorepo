import { NextRequest } from "next/server";

import {
  proxyInventoryResponse,
  proxyToInventoryApi,
  runInventoryBffHandler,
} from "@/lib/api/inventory-server";

export async function POST(request: NextRequest) {
  return runInventoryBffHandler(async () => {
    const body = await request.text();
    const response = await proxyToInventoryApi(request, "/knowledge/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return proxyInventoryResponse(response);
  });
}
