import {
  Supplier,
  SupplierCreatePayload,
  SupplierListFilters,
  SupplierRateUpdatePayload,
  SupplierStatusUpdatePayload,
  SuppliersApiError,
} from "@/types/suppliers";

const API_PREFIX = "/api/suppliers";

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail) && payload.detail.length > 0) {
      const first = payload.detail[0] as { msg?: string };
      if (first.msg) return first.msg;
    }
  } catch {
    // Fall through to status text.
  }
  return response.statusText || "Request failed.";
}

function buildQuery(filters?: SupplierListFilters): string {
  const params = new URLSearchParams();
  if (filters?.country) params.set("country", filters.country);
  if (filters?.category) params.set("category", filters.category);
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function fetchSuppliers(filters?: SupplierListFilters): Promise<Supplier[]> {
  const response = await fetch(`${API_PREFIX}${buildQuery(filters)}`);

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new SuppliersApiError(message, response.status);
  }

  return (await response.json()) as Supplier[];
}

export async function createSupplier(payload: SupplierCreatePayload): Promise<Supplier> {
  const response = await fetch(API_PREFIX, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new SuppliersApiError(message, response.status);
  }

  return (await response.json()) as Supplier;
}

export async function updateSupplierRate(
  id: number,
  payload: SupplierRateUpdatePayload
): Promise<Supplier> {
  const response = await fetch(`${API_PREFIX}/${id}/rate`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new SuppliersApiError(message, response.status);
  }

  return (await response.json()) as Supplier;
}

export async function updateSupplierStatus(
  id: number,
  payload: SupplierStatusUpdatePayload
): Promise<Supplier> {
  const response = await fetch(`${API_PREFIX}/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new SuppliersApiError(message, response.status);
  }

  return (await response.json()) as Supplier;
}

export function formatRate(rate: number, currency: string): string {
  return `${rate.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${currency}`;
}

export function sortSuppliersByName(suppliers: Supplier[]): Supplier[] {
  return [...suppliers].sort((a, b) =>
    a.name.localeCompare(b.name, undefined, { sensitivity: "base" })
  );
}

export async function deleteSupplier(id: number): Promise<void> {
  const response = await fetch(`${API_PREFIX}/${id}`, { method: "DELETE" });

  if (response.status === 204) {
    return;
  }

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new SuppliersApiError(message, response.status);
  }
}
