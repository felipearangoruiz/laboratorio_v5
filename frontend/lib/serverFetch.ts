import { cookies } from "next/headers";

export async function serverFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8000";
  const url = `${baseUrl}${path}`;

  const cookieStore = cookies();
  const authToken = cookieStore.get("auth_token")?.value;
  const headers = new Headers(options.headers);

  if (authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    throw new Error("UNAUTHORIZED");
  }

  if (!response.ok) {
    let details = "";

    try {
      details = await response.text();
    } catch {
      details = "";
    }

    throw new Error(`Error ${response.status} al llamar ${path}${details ? `: ${details}` : ""}`);
  }

  return (await response.json()) as T;
}
