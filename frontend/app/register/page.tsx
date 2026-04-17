"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register, login, getMe, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await register(email, password, name, orgName);
      await login(email, password);
      const user = await getMe();
      // Always go to canvas — register creates an org
      router.push(`/org/${user.organization_id}/canvas`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Error de conexión. Intenta de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-gray-900 text-center">
          Crear cuenta
        </h1>
        <p className="mt-2 text-sm text-gray-500 text-center">
          Accede al canvas organizacional y diagnóstico con IA
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          {error && (
            <div className="p-3 text-sm text-red-700 bg-red-50 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">
              Tu nombre
            </label>
            <input
              id="name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
              placeholder="María García"
            />
          </div>

          <div>
            <label htmlFor="orgName" className="block text-sm font-medium text-gray-700">
              Nombre de tu organización
            </label>
            <input
              id="orgName"
              type="text"
              required
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
              placeholder="Mi Empresa S.A.S."
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Correo electrónico
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
              placeholder="tu@email.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
              placeholder="Mínimo 8 caracteres"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
          >
            {loading ? "Creando cuenta..." : "Crear cuenta"}
          </button>
        </form>

        <div className="mt-6 text-center space-y-2">
          <p className="text-sm text-gray-500">
            ¿Ya tienes cuenta?{" "}
            <Link href="/login" className="text-gray-900 font-medium hover:underline">
              Inicia sesión
            </Link>
          </p>
          <p className="text-sm text-gray-500">
            ¿Solo quieres probar?{" "}
            <Link href="/onboarding" className="text-gray-900 font-medium hover:underline">
              Diagnóstico gratis sin cuenta
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
