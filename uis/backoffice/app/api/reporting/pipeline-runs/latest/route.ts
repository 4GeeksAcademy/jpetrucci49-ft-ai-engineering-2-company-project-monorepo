import { NextRequest } from "next/server";

import {
  proxyInventoryResponse,
  proxyToInventoryApi,
  runInventoryBffHandler,
} from "@/lib/api/inventory-server";

export async function GET(request: NextRequest) {
  return runInventoryBffHandler(async () => {
    const response = await proxyToInventoryApi(request, "/reporting/pipeline-runs/latest");
    return proxyInventoryResponse(response);
  });
}
