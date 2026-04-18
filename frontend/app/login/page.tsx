"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const body = new URLSearchParams({ username: email, password });
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
        credentials: "include",
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Credenciales incorrectas");
      }

      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);

      // Fetch user profile to decide where to send them. Premium flow:
      //   - user con organization_id → /org/{id}/canvas
      //   - user sin organization_id → /register (completar datos de org)
      try {
        const meRes = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${data.access_token}` },
          credentials: "include",
        });
        if (meRes.ok) {
          const me = await meRes.json();
          if (me.organization_id) {
            router.push(`/org/${me.organization_id}/canvas`);
            return;
          }
          router.push("/register");
          return;
        }
      } catch {
        // si falla /me por cualquier razón, caemos al canvas genérico
      }
      // Fallback defensivo: el canvas lee la org del user via useAuth, así que
      // empujar a una ruta canvas con placeholder también funciona.
      router.push("/org/me/canvas");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center">
          <h1 className="text-xl font-semibold text-gray-900">
            Iniciar sesión
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Accede a tu diagnóstico organizacional
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700"
            >
              Correo electrónico
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
              placeholder="tu@correo.com"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700"
            >
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Iniciar sesión
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          ¿No tienes cuenta?{" "}
          <Link
            href="/register"
            className="font-medium text-brand-600 hover:text-brand-700"
          >
            Regístrate gratis
          </Link>
        </p>
      </div>
    </div>
  );
}
