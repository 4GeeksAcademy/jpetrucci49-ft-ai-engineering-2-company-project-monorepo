"use client";

import type { ApiValidationError } from "./types";

export async function parseApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail) && payload.detail.length > 0) {
      const first = payload.detail[0] as ApiValidationError;
      if (first.msg) return first.msg;
    }
  } catch {
    // Fall through.
  }
  return response.statusText || "Request failed.";
}

export async function parseApiFieldErrors(
  response: Response
): Promise<Record<string, string>> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (!Array.isArray(payload.detail)) return {};

    const errors: Record<string, string> = {};
    for (const item of payload.detail as ApiValidationError[]) {
      const field = item.loc[item.loc.length - 1];
      if (typeof field === "string") {
        errors[field] = item.msg;
      }
    }
    return errors;
  } catch {
    return {};
  }
}
