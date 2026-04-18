import type { NextRequest } from "next/server";

export const runtime = "nodejs";
const AUTH_SESSION_COOKIE_NAME = "ck_v2_auth_token";
const AUTH_PRESENCE_COOKIE_NAME = "ck_v2_auth_present";

function normalizeProxyTarget(rawTarget?: string) {
  if (!rawTarget) {
    return "";
  }
  const target =
    rawTarget.startsWith("http://") || rawTarget.startsWith("https://")
      ? rawTarget
      : `http://${rawTarget}`;
  return target.endsWith("/") ? target.slice(0, -1) : target;
}

function resolveBackendBaseUrl() {
  const explicitBaseUrl = process.env.CK_V2_INTERNAL_API_BASE_URL || "";
  const hostportTarget = process.env.CK_V2_INTERNAL_API_HOSTPORT || "";
  return normalizeProxyTarget(explicitBaseUrl || hostportTarget);
}

async function proxyAuthRequest(request: NextRequest, pathSegments: string[]) {
  const backendBaseUrl = resolveBackendBaseUrl();
  if (!backendBaseUrl) {
    return Response.json(
      { detail: "Auth proxy hedefi tanımlı değil." },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }

  const targetPath = pathSegments.length > 0 ? pathSegments.join("/") : "";
  const targetUrl = new URL(`${backendBaseUrl}/api/auth/${targetPath}`);
  targetUrl.search = request.nextUrl.search;

  const outgoingHeaders = new Headers();
  const contentType = request.headers.get("content-type");
  const authorization = request.headers.get("authorization");
  const cookie = request.headers.get("cookie");

  if (contentType) {
    outgoingHeaders.set("content-type", contentType);
  }
  if (authorization) {
    outgoingHeaders.set("authorization", authorization);
  }
  if (cookie) {
    outgoingHeaders.set("cookie", cookie);
  }

  const upstreamResponse = await fetch(targetUrl, {
    method: request.method,
    headers: outgoingHeaders,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  const upstreamContentType = upstreamResponse.headers.get("content-type");
  if (upstreamContentType) {
    responseHeaders.set("content-type", upstreamContentType);
  }
  responseHeaders.set("cache-control", "no-store");

  const setCookieHeaders = typeof upstreamResponse.headers.getSetCookie === "function"
    ? upstreamResponse.headers.getSetCookie()
    : [];
  for (const headerValue of setCookieHeaders) {
    responseHeaders.append("set-cookie", headerValue);
  }

  const responseBody = await upstreamResponse.text();
  const targetAction = targetPath.toLowerCase();
  const isJsonResponse = (upstreamContentType || "").toLowerCase().includes("application/json");

  if (upstreamResponse.ok && isJsonResponse && (targetAction === "login" || targetAction === "verify-phone-code")) {
    try {
      const payload = JSON.parse(responseBody) as {
        access_token?: string;
        expires_at?: string;
      };
      const token = String(payload.access_token || "").trim();
      const expiresAt = String(payload.expires_at || "").trim();
      if (token) {
        const nowMs = Date.now();
        const expiryMs = Date.parse(expiresAt);
        const fallbackMaxAge = 30 * 24 * 60 * 60;
        const maxAge = Number.isFinite(expiryMs) && expiryMs > nowMs
          ? Math.max(Math.floor((expiryMs - nowMs) / 1000), 1)
          : fallbackMaxAge;
        responseHeaders.append(
          "set-cookie",
          `${AUTH_SESSION_COOKIE_NAME}=${encodeURIComponent(token)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`,
        );
        responseHeaders.append(
          "set-cookie",
          `${AUTH_PRESENCE_COOKIE_NAME}=1; Path=/; Secure; SameSite=Lax; Max-Age=${maxAge}`,
        );
      }
    } catch {
      // Pass through the upstream body even if cookie synthesis fails.
    }
  }

  if (targetAction === "logout") {
    responseHeaders.append(
      "set-cookie",
      `${AUTH_SESSION_COOKIE_NAME}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`,
    );
    responseHeaders.append(
      "set-cookie",
      `${AUTH_PRESENCE_COOKIE_NAME}=; Path=/; Secure; SameSite=Lax; Max-Age=0`,
    );
  }

  return new Response(responseBody, {
    status: upstreamResponse.status,
    headers: responseHeaders,
  });
}

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyAuthRequest(request, path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyAuthRequest(request, path);
}
