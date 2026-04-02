import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Protected routes that require authentication
const PROTECTED_PATHS = ["/dashboard", "/agents", "/system"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip protection for /login and /api/* paths
  if (pathname.startsWith("/login") || pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  // Check if the current path needs protection
  const isProtected = PROTECTED_PATHS.some((path) =>
    pathname === path || pathname.startsWith(path + "/")
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  // Check for auth token in cookies
  const token = request.cookies.get("token")?.value;

  if (!token) {
    // No token found — redirect to login
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Run middleware on all paths except static assets
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
