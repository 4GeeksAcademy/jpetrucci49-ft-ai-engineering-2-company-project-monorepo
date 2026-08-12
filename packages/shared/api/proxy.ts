/** FastAPI origin for server-side BFF proxies. */
export function getFastApiOrigin(): string {
  const configured =
    process.env.AUTH_API_URL ??
    process.env.SUPPLIERS_API_URL ??
    process.env.INCIDENTS_API_URL ??
    "http://127.0.0.1:8000";
  return configured.replace(/\/$/, "");
}

/** Forward the browser bearer token to FastAPI unchanged. */
export function forwardAuthorization(
  authorization: string | null,
  headers?: HeadersInit
): Headers {
  const merged = new Headers(headers);
  if (authorization) {
    merged.set("Authorization", authorization);
  }
  return merged;
}
