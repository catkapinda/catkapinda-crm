import { buildPreviewResponse, isPreviewModeBrowser } from "./preview";

export const AUTH_TOKEN_COOKIE_NAME = "ck_v2_auth_token";
export const AUTH_PRESENCE_COOKIE_NAME = "ck_v2_auth_present";
export const AUTH_NOTICE_STORAGE_KEY = "ck_v2_auth_notice";
export const AUTH_UNAUTHORIZED_EVENT = "ck-v2-auth-unauthorized";

let unauthorizedSessionCheck: Promise<boolean> | null = null;

export function resolveApiBaseUrl() {
  const rawConfiguredBaseUrl =
    process.env.NEXT_PUBLIC_V2_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "/v2-api";
  const configuredBaseUrl = rawConfiguredBaseUrl.trim();
  const effectiveBaseUrl =
    !configuredBaseUrl || configuredBaseUrl === "/" || configuredBaseUrl === "/api"
      ? "/v2-api"
      : configuredBaseUrl;
  if (effectiveBaseUrl.startsWith("/")) {
    return effectiveBaseUrl.endsWith("/") ? effectiveBaseUrl.slice(0, -1) : effectiveBaseUrl;
  }
  return effectiveBaseUrl.endsWith("/api") ? effectiveBaseUrl : `${effectiveBaseUrl}/api`;
}

export function writeAuthPresenceMarker(active: boolean) {
  if (typeof window === "undefined") {
    return;
  }
  const secureFlag = window.location.protocol === "https:" ? "; Secure" : "";
  if (active) {
    document.cookie = `${AUTH_PRESENCE_COOKIE_NAME}=1; Path=/; SameSite=Lax; Max-Age=${60 * 60 * 12}${secureFlag}`;
    return;
  }
  document.cookie = `${AUTH_PRESENCE_COOKIE_NAME}=; Path=/; SameSite=Lax; Max-Age=0${secureFlag}`;
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
  if (normalizedPath === "/auth" || normalizedPath.startsWith("/auth/")) {
    return `/api${normalizedPath}`;
  }
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

async function shouldEmitUnauthorized(path: string) {
  if (path.startsWith("/auth/login") || path.startsWith("/auth/verify-phone-code")) {
    return false;
  }
  if (path.startsWith("/auth/me")) {
    return true;
  }
  if (!unauthorizedSessionCheck) {
    unauthorizedSessionCheck = fetch(buildApiUrl("/auth/me"), {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then((response) => !response.ok)
      .catch(() => false)
      .finally(() => {
        unauthorizedSessionCheck = null;
      });
  }
  return unauthorizedSessionCheck;
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
  if (response.status === 401 && (await shouldEmitUnauthorized(path))) {
    emitUnauthorizedEvent();
  }
  return response;
}

export async function apiErrorMessage(response: Response, fallback: string) {
  try {
    const payload = (await response.clone().json()) as {
      detail?: unknown;
      message?: unknown;
    } | null;
    const detail = payload?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length) {
      return detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }
          if (item && typeof item === "object" && "msg" in item) {
            return String(item.msg || "");
          }
          return "";
        })
        .filter(Boolean)
        .join(" ");
    }
    if (typeof payload?.message === "string" && payload.message.trim()) {
      return payload.message;
    }
  } catch {
    try {
      const text = await response.clone().text();
      if (text.trim()) {
        return text.trim().slice(0, 220);
      }
    } catch {
      // Keep the user-facing fallback below.
    }
  }
  return fallback;
}
