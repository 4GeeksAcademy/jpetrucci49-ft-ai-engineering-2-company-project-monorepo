import { AnalysisResult, IncidentsApiError } from "@/types/incidents";

function getBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new IncidentsApiError("NEXT_PUBLIC_API_URL is not configured.", 0);
  }
  return baseUrl.replace(/\/$/, "");
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

export async function analyzeIncidents(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${getBaseUrl()}/api/incidents/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new IncidentsApiError(message, response.status);
  }

  return (await response.json()) as AnalysisResult;
}

export async function exportIncidentResults(): Promise<Blob> {
  const response = await fetch(`${getBaseUrl()}/api/incidents/results/export`);

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new IncidentsApiError(message, response.status);
  }

  return response.blob();
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
