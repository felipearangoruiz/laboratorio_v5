import Link from "next/link";
import { ArrowRight, BarChart3, Users, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-warm-50">
      {/* ── Header ── */}
      <header className="sticky top-0 z-50 border-b border-warm-200 bg-warm-50/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <span className="font-display italic text-xl text-warm-900 tracking-tight">
            Laboratorio
          </span>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-warm-500 hover:text-warm-900 transition-colors"
            >
              Iniciar sesión
            </Link>
            <Link
              href="/onboarding"
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors shadow-warm-sm"
            >
              Comenzar gratis
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <main className="flex flex-1 flex-col px-6 pt-24 pb-20 relative overflow-hidden">
        {/* Subtle dot pattern */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(#1C1917 1px, transparent 1px)",
            backgroundSize: "28px 28px",
            opacity: 0.03,
          }}
        />

        <div className="relative mx-auto w-full max-w-3xl">
          {/* Eyebrow */}
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent mb-5">
            Diagnóstico organizacional asistido por IA
          </p>

          {/* Hero headline */}
          <h1 className="font-display text-5xl sm:text-6xl leading-[1.08] text-warm-900">
            Entiende cómo funciona{" "}
            <em className="italic text-accent">realmente</em>
            <br className="hidden sm:block" />
            {" "}tu organización
          </h1>

          <p className="mt-6 max-w-xl text-lg leading-relaxed text-warm-500">
            Captura la percepción de tu equipo, identifica tensiones ocultas
            y recibe recomendaciones accionables. Resultados en 10 minutos.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-2 rounded-md bg-accent px-6 py-3 text-sm font-semibold text-white hover:bg-accent-hover transition-colors shadow-warm-sm"
            >
              Diagnostica tu organización
              <ArrowRight className="h-4 w-4" />
            </Link>
            <span className="text-sm text-warm-400">
              Gratis · sin tarjeta · 10 minutos
            </span>
          </div>
        </div>

        {/* ── Divider ── */}
        <div className="relative mx-auto mt-24 w-full max-w-3xl">
          <div className="border-t border-warm-200" />
        </div>

        {/* ── Features ── */}
        <div className="relative mx-auto mt-12 grid w-full max-w-3xl gap-8 sm:grid-cols-3">
          {[
            {
              icon: Users,
              title: "Tu equipo responde",
              body: "Invita 3–5 miembros. Encuesta anónima de 5–8 minutos.",
            },
            {
              icon: Zap,
              title: "Análisis instantáneo",
              body: "Score automático en 4 dimensiones organizacionales.",
            },
            {
              icon: BarChart3,
              title: "Radar de tu organización",
              body: "Visualiza fortalezas y áreas de mejora de un vistazo.",
            },
          ].map((f) => (
            <div key={f.title} className="flex flex-col gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-md border border-warm-200 bg-white shadow-warm-sm">
                <f.icon className="h-4 w-4 text-warm-500" />
              </div>
              <h3 className="text-sm font-semibold text-warm-900">{f.title}</h3>
              <p className="text-sm leading-relaxed text-warm-500">{f.body}</p>
            </div>
          ))}
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-warm-200 py-6">
        <div className="mx-auto max-w-5xl px-6 text-center text-xs text-warm-400">
          © {new Date().getFullYear()} Laboratorio de Modelamiento Institucional
        </div>
      </footer>
    </div>
  );
}
