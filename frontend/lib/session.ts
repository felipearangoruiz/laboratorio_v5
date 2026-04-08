import { cookies } from "next/headers";
import { decodeJwt, jwtVerify } from "jose";
import type { JWTPayload } from "./types";

function isSessionPayload(payload: unknown): payload is JWTPayload {
  if (!payload || typeof payload !== "object") {
    return false;
  }

  const candidate = payload as Record<string, unknown>;

  return (
    typeof candidate.user_id === "string" &&
    typeof candidate.role === "string" &&
    typeof candidate.organization_id === "string"
  );
}

export async function getSessionPayload(): Promise<JWTPayload | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;

  if (!token) {
    return null;
  }

  const jwtSecret = process.env.JWT_SECRET;

  try {
    if (!jwtSecret) {
      if (process.env.NODE_ENV === "production") {
        return null;
      }

      const decodedPayload = decodeJwt(token);
      return isSessionPayload(decodedPayload) ? decodedPayload : null;
    }

    const secret = new TextEncoder().encode(jwtSecret);
    const { payload } = await jwtVerify(token, secret);

    return isSessionPayload(payload) ? payload : null;
  } catch {
    return null;
  }
}
