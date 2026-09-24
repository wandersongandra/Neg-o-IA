export const DEV_SESSION_COOKIE = "sophie_session";
export const PROD_SESSION_COOKIE = "__Host-sophie_session";

interface CookieReader {
  get(name: string): { value: string } | undefined;
}

export function sessionCookieName(): string {
  return process.env.NODE_ENV === "production"
    ? PROD_SESSION_COOKIE
    : DEV_SESSION_COOKIE;
}

export function getSessionToken(cookies: CookieReader): string | undefined {
  return cookies.get(sessionCookieName())?.value;
}
