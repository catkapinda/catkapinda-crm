import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { AUTH_PRESENCE_COOKIE_NAME } from "./lib/api";

const PUBLIC_PATHS = new Set(["/login", "/status"]);

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (
    PUBLIC_PATHS.has(pathname) ||
    pathname === "/preview" ||
    pathname.startsWith("/preview/") ||
    pathname.startsWith("/v2-api/")
  ) {
    return NextResponse.next();
  }

  const authToken = request.cookies.get(AUTH_PRESENCE_COOKIE_NAME)?.value ?? "";
  if (authToken) {
    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = `?next=${encodeURIComponent(`${pathname}${search}`)}`;
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!api|v2-api|_next/static|_next/image|favicon.ico).*)"],
};
