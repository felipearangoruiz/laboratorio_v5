"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const regRes = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, org_name: orgName }),
      });

      if (!regRes.ok) {
        const data = await regRes.json().catch(() => ({}));
        throw new Error(data.detail ?? "Error al registrarse");
      }

      const regData = await regRes.json();
      const organizationId: string | undefined = regData.organization_id;

      const loginBody = new URLSearchParams({ username: email, password });
      const loginRes = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: loginBody,
        credentials: "include",
      });

      if (loginRes.ok) {
        const data = await loginRes.json();
        localStorage.setItem("access_token", data.access_token);
      }

      if (organizationId) {
        router.push(`/org/${organizationId}/canvas`);
      } else {
        router.push("/org/me/canvas");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al registrarse");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-warm-50 px-4 py-12">
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
              Crear cuenta
            </h1>
            <p className="mt-1 text-sm text-warm-500">
              Conoce cómo está tu organización en 10 minutos
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
                {error}
              </div>
            )}

            {[
              { id: "name",    label: "Tu nombre",              type: "text",     value: name,    setter: setName,    placeholder: "Tu nombre" },
              { id: "orgName", label: "Nombre de la organización", type: "text", value: orgName, setter: setOrgName, placeholder: "Ej: Specialized Colombia" },
              { id: "email",   label: "Correo electrónico",     type: "email",    value: email,   setter: setEmail,   placeholder: "tu@correo.com" },
            ].map((f) => (
              <div key={f.id}>
                <label htmlFor={f.id} className="block text-sm font-medium text-warm-900 mb-1.5">
                  {f.label}
                </label>
                <input
                  id={f.id}
                  type={f.type}
                  required
                  value={f.value}
                  onChange={(e) => f.setter(e.target.value)}
                  className="block w-full rounded-md border border-warm-300 bg-white px-3 py-2.5 text-sm text-warm-900 placeholder:text-warm-400 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                  placeholder={f.placeholder}
                />
              </div>
            ))}

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-warm-900 mb-1.5">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full rounded-md border border-warm-300 bg-white px-3 py-2.5 text-sm text-warm-900 placeholder:text-warm-400 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                placeholder="Mínimo 8 caracteres"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Crear cuenta
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-warm-500">
          ¿Ya tienes cuenta?{" "}
          <Link href="/login" className="font-medium text-accent hover:text-accent-hover">
            Iniciar sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
