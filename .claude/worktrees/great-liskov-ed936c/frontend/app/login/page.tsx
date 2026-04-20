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
      router.push("/org/me/canvas");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-warm-50 px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 text-center">
          <Link href="/" className="font-display italic text-2xl text-warm-900">
            Laboratorio
          </Link>
        </div>

        <div className="rounded-lg border border-warm-200 bg-white p-8 shadow-warm-sm">
          <div className="mb-6">
            <h1 className="font-display italic text-2xl text-warm-900">
              Iniciar sesión
            </h1>
            <p className="mt-1 text-sm text-warm-500">
              Accede a tu diagnóstico organizacional
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
                {error}
              </div>
            )}

            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-warm-900 mb-1.5"
              >
                Correo electrónico
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="block w-full rounded-md border border-warm-300 bg-white px-3 py-2.5 text-sm text-warm-900 placeholder:text-warm-400 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                placeholder="tu@correo.com"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-warm-900 mb-1.5"
              >
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full rounded-md border border-warm-300 bg-white px-3 py-2.5 text-sm text-warm-900 placeholder:text-warm-400 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Iniciar sesión
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-warm-500">
          ¿No tienes cuenta?{" "}
          <Link
            href="/register"
            className="font-medium text-accent hover:text-accent-hover"
          >
            Regístrate gratis
          </Link>
        </p>
      </div>
    </div>
  );
}
