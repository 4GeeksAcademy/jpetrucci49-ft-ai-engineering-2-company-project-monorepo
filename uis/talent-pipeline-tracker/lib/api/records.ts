import { apiRequest } from "@/lib/api/client";
import type {
  RecordCreate,
  RecordOut,
  RecordPatch,
  RecordsListParams,
  RecordsListResponse,
} from "@/types/record";

function toSearchParams(params: RecordsListParams): URLSearchParams {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.stage) search.set("stage", params.stage);
  if (params.search) search.set("search", params.search);
  if (params.page) search.set("page", String(params.page));
  if (params.limit) search.set("limit", String(params.limit));
  return search;
}

export function fetchRecords(params: RecordsListParams = {}): Promise<RecordsListResponse> {
  return apiRequest<RecordsListResponse>("/records", { method: "GET" }, toSearchParams(params));
}

export function fetchRecord(id: string): Promise<RecordOut> {
  return apiRequest<RecordOut>(`/records/${id}`, { method: "GET" });
}

export function createRecord(payload: RecordCreate): Promise<RecordOut> {
  return apiRequest<RecordOut>("/records", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function replaceRecord(id: string, payload: RecordCreate): Promise<RecordOut> {
  return apiRequest<RecordOut>(`/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function patchRecord(id: string, payload: RecordPatch): Promise<RecordOut> {
  return apiRequest<RecordOut>(`/records/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
