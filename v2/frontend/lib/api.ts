export const AUTH_TOKEN_STORAGE_KEY = "ck_v2_auth_token";
export const AUTH_NOTICE_STORAGE_KEY = "ck_v2_auth_notice";
export const AUTH_UNAUTHORIZED_EVENT = "ck-v2-auth-unauthorized";

export function resolveApiBaseUrl() {
  const configuredBaseUrl =
    process.env.NEXT_PUBLIC_V2_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "/v2-api";
  return configuredBaseUrl.endsWith("/api") ? configuredBaseUrl : `${configuredBaseUrl}/api`;
}

export function readStoredAuthToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) ?? "";
}

export function writeStoredAuthToken(token: string) {
  if (typeof window === "undefined") {
    return;
  }
  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    return;
  }
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

export function readStoredAuthNotice() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.sessionStorage.getItem(AUTH_NOTICE_STORAGE_KEY) ?? "";
}

export function writeStoredAuthNotice(message: string) {
  if (typeof window === "undefined") {
    return;
  }
  if (message) {
    window.sessionStorage.setItem(AUTH_NOTICE_STORAGE_KEY, message);
    return;
  }
  window.sessionStorage.removeItem(AUTH_NOTICE_STORAGE_KEY);
}

export function buildApiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${resolveApiBaseUrl()}${normalizedPath}`;
}

function emitUnauthorizedEvent() {
  if (typeof window === "undefined") {
    return;
  }
  writeStoredAuthToken("");
  writeStoredAuthNotice("Oturumun sona erdi. Devam etmek icin tekrar giris yap.");
  window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers ?? {});
  const token = readStoredAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers,
    cache: init.cache ?? "no-store",
  });
  if (response.status === 401 && !path.startsWith("/auth/login") && !path.startsWith("/auth/verify-phone-code")) {
    emitUnauthorizedEvent();
  }
  return response;
}
