import { jwtVerify } from "jose";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

export default async function middleware(request: NextRequest) {
  const token = request.cookies.get("auth_token")?.value;
  const jwtSecret = process.env.JWT_SECRET;

  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (!jwtSecret) {
    if (process.env.NODE_ENV === "production") {
      return NextResponse.redirect(new URL("/login", request.url));
    }

    return NextResponse.next();
  }

  try {
    const secret = new TextEncoder().encode(jwtSecret);
    const { payload } = await jwtVerify(token, secret);

    if (payload.role === "admin" && request.nextUrl.pathname.startsWith("/superadmin")) {
      return NextResponse.redirect(new URL("/admin", request.url));
    }

    return NextResponse.next();
  } catch {
    return NextResponse.redirect(new URL("/login", request.url));
  }
}

export const config = {
  matcher: ["/admin/:path*", "/superadmin/:path*"],
};
