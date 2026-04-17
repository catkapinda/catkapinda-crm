import { buildPreviewResponse, isPreviewModeBrowser } from "./preview";

export const AUTH_TOKEN_COOKIE_NAME = "ck_v2_auth_token";
export const AUTH_PRESENCE_COOKIE_NAME = "ck_v2_auth_present";
export const AUTH_NOTICE_STORAGE_KEY = "ck_v2_auth_notice";
export const AUTH_UNAUTHORIZED_EVENT = "ck-v2-auth-unauthorized";

export function resolveApiBaseUrl() {
  const configuredBaseUrl =
    process.env.NEXT_PUBLIC_V2_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "/v2-api";
  if (configuredBaseUrl.startsWith("/")) {
    return configuredBaseUrl.endsWith("/") ? configuredBaseUrl.slice(0, -1) : configuredBaseUrl;
  }
  return configuredBaseUrl.endsWith("/api") ? configuredBaseUrl : `${configuredBaseUrl}/api`;
}

export function writeAuthPresenceMarker(active: boolean) {
  if (typeof window === "undefined") {
    return;
  }
  if (active) {
    document.cookie = `${AUTH_PRESENCE_COOKIE_NAME}=1; Path=/; SameSite=Lax; Max-Age=${60 * 60 * 12}`;
    return;
  }
  document.cookie = `${AUTH_PRESENCE_COOKIE_NAME}=; Path=/; SameSite=Lax; Max-Age=0`;
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
  writeAuthPresenceMarker(false);
  writeStoredAuthNotice("Oturumun sona erdi. Devam etmek için tekrar giriş yap.");
  window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  if (isPreviewModeBrowser()) {
    const previewResponse = buildPreviewResponse(path, init);
    if (previewResponse) {
      return previewResponse;
    }
  }
  const headers = new Headers(init.headers ?? {});
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers,
    credentials: init.credentials ?? "same-origin",
    cache: init.cache ?? "no-store",
  });
  if (response.status === 401 && !path.startsWith("/auth/login") && !path.startsWith("/auth/verify-phone-code")) {
    emitUnauthorizedEvent();
  }
  return response;
}
