import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { AUTH_PRESENCE_COOKIE_NAME } from "./lib/api";

const PUBLIC_PATHS = new Set(["/login", "/status"]);

function applySecurityHeaders(response: NextResponse, request: NextRequest) {
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  response.headers.set("Cross-Origin-Opener-Policy", "same-origin");
  const forwardedProto = request.headers.get("x-forwarded-proto");
  const protocol = request.nextUrl.protocol;
  if (forwardedProto === "https" || protocol === "https:") {
    response.headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload");
  }
  return response;
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (
    PUBLIC_PATHS.has(pathname) ||
    pathname === "/preview" ||
    pathname.startsWith("/preview/") ||
    pathname.startsWith("/v2-api/")
  ) {
    return applySecurityHeaders(NextResponse.next(), request);
  }

  const authToken = request.cookies.get(AUTH_PRESENCE_COOKIE_NAME)?.value ?? "";
  if (authToken) {
    return applySecurityHeaders(NextResponse.next(), request);
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = `?next=${encodeURIComponent(`${pathname}${search}`)}`;
  return applySecurityHeaders(NextResponse.redirect(loginUrl), request);
}

export const config = {
  matcher: ["/((?!api|v2-api|_next/static|_next/image|favicon.ico).*)"],
};
