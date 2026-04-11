export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const url = `${baseUrl}${path}`;

  const authToken = document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith("auth_token="))
    ?.split("=")[1];

  const headers = new Headers(options.headers);

  if (authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("No autorizado. Redirigiendo a /login.");
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
