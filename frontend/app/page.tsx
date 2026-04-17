"use client";

import Link from "next/link";
import { ArrowRight, BarChart3, Users, Zap } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-gray-100 px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <span className="text-lg font-semibold text-gray-900">
          Laboratorio Institucional
        </span>
        <div className="flex gap-3">
          <Link
            href="/login"
            className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900"
          >
            Iniciar sesión
          </Link>
          <Link
            href="/register"
            className="px-4 py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800"
          >
            Comenzar gratis
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-20 pb-16 text-center">
        <h1 className="text-4xl font-bold text-gray-900 leading-tight sm:text-5xl">
          Descubre cómo funciona tu organización por dentro
        </h1>
        <p className="mt-6 text-lg text-gray-600 leading-relaxed">
          Un diagnóstico rápido con tu equipo. Responde una encuesta corta,
          invita a tus miembros y obtén un mapa real de liderazgo, comunicación,
          cultura y operación.
        </p>
        <Link
          href="/register"
          className="mt-8 inline-flex items-center gap-2 px-6 py-3 bg-gray-900 text-white rounded-lg text-base font-medium hover:bg-gray-800"
        >
          Diagnosticar mi organización
          <ArrowRight className="w-4 h-4" />
        </Link>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 pb-20 grid sm:grid-cols-3 gap-8">
        <FeatureCard
          icon={<Zap className="w-6 h-6 text-amber-500" />}
          title="5 minutos"
          description="Encuesta corta para ti y tu equipo. Sin configuración compleja."
        />
        <FeatureCard
          icon={<Users className="w-6 h-6 text-blue-500" />}
          title="Perspectiva del equipo"
          description="Tus miembros responden de forma anónima. Mínimo 3 respuestas."
        />
        <FeatureCard
          icon={<BarChart3 className="w-6 h-6 text-emerald-500" />}
          title="Score radar"
          description="Visualiza fortalezas y áreas de mejora en 4 dimensiones clave."
        />
      </section>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="border border-gray-100 rounded-xl p-6">
      <div className="mb-3">{icon}</div>
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      <p className="mt-1 text-sm text-gray-500">{description}</p>
    </div>
  );
}
