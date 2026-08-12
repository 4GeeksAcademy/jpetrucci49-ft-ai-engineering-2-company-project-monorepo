export const TOKEN_STORAGE_KEY = "healthcore_access_token";
const TOKEN_COOKIE_NAME = "healthcore_access_token";

/** localhost / 127.0.0.1 cookies are shared across ports — use as cross-app sync in local dev. */
function usesSharedHostCookie(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

function readCookieToken(): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${TOKEN_COOKIE_NAME}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

function writeCookieToken(token: string): void {
  if (!usesSharedHostCookie()) return;
  const maxAge = 60 * 60 * 24;
  document.cookie = `${TOKEN_COOKIE_NAME}=${encodeURIComponent(token)}; path=/; SameSite=Lax; max-age=${maxAge}`;
}

function eraseCookieToken(): void {
  if (!usesSharedHostCookie()) return;
  document.cookie = `${TOKEN_COOKIE_NAME}=; path=/; max-age=0`;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;

  const stored = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  const fromCookie = readCookieToken();

  if (usesSharedHostCookie()) {
    if (stored && !fromCookie) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
      return null;
    }
    if (!stored && fromCookie) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, fromCookie);
      return fromCookie;
    }
  }

  return stored ?? fromCookie;
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  writeCookieToken(token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  eraseCookieToken();
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}
