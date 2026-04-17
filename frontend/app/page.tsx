import Link from "next/link";
import { ArrowRight, BarChart3, Users, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <span className="text-lg font-semibold tracking-tight text-gray-900">
            Laboratorio
          </span>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-gray-600 hover:text-gray-900"
            >
              Iniciar sesión
            </Link>
            <Link
              href="/onboarding"
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              Comenzar gratis
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="flex flex-1 flex-col items-center justify-center px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            Entiende cómo funciona{" "}
            <span className="text-brand-600">realmente</span> tu organización
          </h1>
          <p className="mt-4 text-lg text-gray-500">
            Diagnóstico organizacional asistido por IA. Captura la percepción de
            tu equipo, identifica tensiones ocultas y recibe recomendaciones
            accionables.
          </p>
          <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-6 py-3 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              Diagnostica tu organización
              <ArrowRight className="h-4 w-4" />
            </Link>
            <span className="text-sm text-gray-400">
              Gratis — resultados en 10 minutos
            </span>
          </div>
        </div>

        {/* Features */}
        <div className="mx-auto mt-20 grid max-w-3xl gap-8 sm:grid-cols-3">
          <div className="text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50">
              <Users className="h-5 w-5 text-brand-600" />
            </div>
            <h3 className="mt-3 text-sm font-semibold text-gray-900">
              Tu equipo responde
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Invita a 3-5 miembros. Encuesta corta de 5 minutos.
            </p>
          </div>
          <div className="text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50">
              <Zap className="h-5 w-5 text-brand-600" />
            </div>
            <h3 className="mt-3 text-sm font-semibold text-gray-900">
              Análisis instantáneo
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Score automático en 4 dimensiones organizacionales.
            </p>
          </div>
          <div className="text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50">
              <BarChart3 className="h-5 w-5 text-brand-600" />
            </div>
            <h3 className="mt-3 text-sm font-semibold text-gray-900">
              Radar de tu organización
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Visualiza fortalezas y áreas de mejora de un vistazo.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
