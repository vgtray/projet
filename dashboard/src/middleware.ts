import { NextRequest, NextResponse } from "next/server";
import { getSessionCookie } from "better-auth/cookies";

const publicPaths = ["/login", "/api/auth"];

export async function middleware(request: NextRequest) {
  const session = getSessionCookie(request);
  const { pathname } = request.nextUrl;

  const isPublicPath = publicPaths.some((path) => pathname.startsWith(path));

  if (!session) {
    if (!isPublicPath) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
  } else if (pathname === "/login") {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
