import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-white">
      <div className="mx-auto max-w-5xl">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
          Laboratorio
        </p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-tight md:text-6xl">
          Captura entrevistas organizacionales y conviértelas en lectura diagnóstica.
        </h1>
        <p className="mt-6 max-w-2xl text-base leading-7 text-slate-300 md:text-lg">
          Esta versión prioriza un flujo simple: ordenar la organización, cargar personas,
          completar entrevistas y revisar resultados desde una vista central del caso.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/login"
            className="rounded-xl bg-white px-5 py-3 text-sm font-medium text-slate-950 hover:bg-slate-200"
          >
            Iniciar sesión
          </Link>
          <Link
            href="/admin"
            className="rounded-xl border border-slate-700 px-5 py-3 text-sm font-medium text-slate-100 hover:bg-slate-900"
          >
            Ir al resumen del caso
          </Link>
        </div>
      </div>
    </main>
  );
}
