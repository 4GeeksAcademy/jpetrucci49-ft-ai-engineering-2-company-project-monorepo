import { getToken, setToken } from "./token";

const HASH_PARAM = "access_token";

/** Append token hash when linking to another internal app (fallback when cookies cannot sync). */
export function buildAuthenticatedAppUrl(url: string): string {
  const token = getToken();
  if (!token) return url;

  try {
    const target = new URL(url);
    target.hash = `${HASH_PARAM}=${encodeURIComponent(token)}`;
    return target.toString();
  } catch {
    return url;
  }
}

/** Read token from URL hash (cross-app navigation), store locally, and strip from the address bar. */
export function consumeTokenFromHash(): boolean {
  if (typeof window === "undefined") return false;

  const raw = window.location.hash.replace(/^#/, "");
  if (!raw) return false;

  const token = new URLSearchParams(raw).get(HASH_PARAM);
  if (!token) return false;

  setToken(token);
  window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  return true;
}

/** Run on app startup before auth checks. */
export function bootstrapAuthSession(): void {
  consumeTokenFromHash();
  getToken();
}
