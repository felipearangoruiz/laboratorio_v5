// ============================================================
// Sprint 2.2 — auth utilities consolidadas
// ============================================================
// Reemplazo centralizado para los múltiples sitios donde se
// leía `localStorage.getItem("access_token")` y se construía
// manualmente un header `Authorization: Bearer ...`.
//
// Expone funciones puras (no hooks). Para un hook reactivo ver
// `hooks/useAuth.ts`.
//
// Notas de implementación:
// - Caché en memoria: evita un `localStorage.getItem` por cada
//   request. Se invalida vía `storage` event (cuando otra tab
//   cambia el token) y explícitamente vía `clearAuth()`.
// - SSR-safe: si `typeof window === "undefined"` devuelve null
//   o `{}` según el caso, nunca toca `localStorage`.

const TOKEN_KEY = "access_token";

let cachedToken: string | null = null;
let cacheInitialized = false;
let storageListenerAttached = false;

function ensureCacheInitialized(): void {
  if (cacheInitialized) return;
  if (typeof window === "undefined") return;
  cachedToken = window.localStorage.getItem(TOKEN_KEY);
  cacheInitialized = true;

  if (!storageListenerAttached) {
    window.addEventListener("storage", (event: StorageEvent) => {
      if (event.key === TOKEN_KEY || event.key === null) {
        cachedToken = window.localStorage.getItem(TOKEN_KEY);
      }
    });
    storageListenerAttached = true;
  }
}

/**
 * Devuelve el access_token actual (o null si no hay sesión /
 * estamos en SSR). Usa caché en memoria con invalidación vía
 * `storage` event.
 */
export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  ensureCacheInitialized();
  return cachedToken;
}

/**
 * Header spreadable de autorización. Vacío si no hay token.
 *
 * Uso:
 *   fetch(url, { headers: { "Content-Type": "application/json", ...authHeader() } })
 */
export function authHeader(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Borra el token del storage y del caché en memoria. */
export function clearAuth(): void {
  cachedToken = null;
  cacheInitialized = true; // mantener marcada; el listener gestiona cambios
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

/**
 * Setter interno — usado por `login()` en `lib/api.ts` para
 * mantener el caché sincronizado sin tener que esperar el
 * próximo `storage` event (que no dispara en la misma tab).
 */
export function setAuthToken(token: string): void {
  cachedToken = token;
  cacheInitialized = true;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(TOKEN_KEY, token);
  }
}
