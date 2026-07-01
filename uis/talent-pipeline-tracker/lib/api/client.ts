import { ApiError } from "@/types/api";

function getBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  }
  return baseUrl.replace(/\/$/, "");
}

function buildUrl(path: string, searchParams?: URLSearchParams): string {
  const url = `${getBaseUrl()}${path}`;
  if (!searchParams || [...searchParams.keys()].length === 0) return url;
  return `${url}?${searchParams.toString()}`;
}

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

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
  searchParams?: URLSearchParams
): Promise<T> {
  const response = await fetch(buildUrl(path, searchParams), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
