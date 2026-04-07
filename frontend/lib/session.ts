import { cookies } from "next/headers";
import { jwtVerify } from "jose";
import type { JWTPayload } from "./types";

export async function getSessionPayload(): Promise<JWTPayload | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;

  if (!token) {
    return null;
  }

  if (!process.env.JWT_SECRET) {
    throw new Error("JWT_SECRET is not defined");
  }

  try {
    const secret = new TextEncoder().encode(process.env.JWT_SECRET);
    const { payload } = await jwtVerify(token, secret);

    return payload as JWTPayload;
  } catch {
    return null;
  }
}
