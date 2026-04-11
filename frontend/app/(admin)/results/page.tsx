import { redirect } from "next/navigation";

import { serverFetch } from "@/lib/serverFetch";
import { getSessionPayload } from "@/lib/session";
import TriggerDiagnosisButton from "./TriggerDiagnosisButton";

type ResultRow = {
  id: string;
  organization_id: string;
  group_id: string | null;
  type: string;
  result: Record<string, unknown>;
  created_at: string;
};

type LatestJob = {
  id: string;
  status: string;
  error: string | null;
  created_at: string;
  updated_at: string;
} | null;

type DashboardInfo = {
  can_generate_diagnosis: boolean;
  strategic_context: {
    is_complete: boolean;
  };
};

function formatResultType(type: string) {
  if (type === "orientado") {
    return "Reporte orientado";
  }

  if (type === "ciego") {
    return "Reporte ciego";
  }

  if (type === "orientacion") {
    return "Orientación";
  }

  return type;
}

function stringifyValue(value: unknown) {
  if (typeof value === "string") {
    return value.trim() || "Sin contenido";
  }

  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(" · ") : "Sin contenido";
  }

  if (value && typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }

  if (value == null) {
    return "Sin contenido";
  }

  return String(value);
}

export default async function ResultsPage() {
  const session = await getSessionPayload();

  if (!session?.organization_id) {
    redirect("/login");
  }

  try {
    const results = await serverFetch<ResultRow[]>(
      `/organizations/${session.organization_id}/results`
    );
    const latestJob = await serverFetch<LatestJob>(
      `/organizations/${session.organization_id}/results/status/latest`
    );
    const dashboard = await serverFetch<DashboardInfo>(
      `/organizations/${session.organization_id}/dashboard`
    );
    const canGenerate = dashboard.can_generate_diagnosis;
    const hasStrategicContext = dashboard.strategic_context.is_complete;

    return (
      <main className="space-y-6 p-6 md:p-8">
        <header className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
            Resultados
          </p>
          <h1 className="text-3xl font-semibold text-slate-900">Diagnóstico básico</h1>
          <p className="max-w-3xl text-sm leading-6 text-slate-600 md:text-base">
            Esta sección presenta el resultado más reciente disponible para la organización y el
            historial guardado. Si todavía no existe un procesamiento, el estado vacío sigue siendo
            explícito para el usuario.
          </p>
        </header>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Procesamiento</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                El diagnóstico básico se genera a partir de las entrevistas completadas y queda
                guardado como resultado reutilizable. {hasStrategicContext
                  ? "También incorpora el contexto estratégico cargado por el admin."
                  : "Todavía puede enriquecerse si el admin carga el contexto estratégico del caso."}
              </p>
            </div>

            <TriggerDiagnosisButton organizationId={session.organization_id} disabled={!canGenerate} />
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <article className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Último job
              </p>
              <p className="mt-2 text-sm text-slate-800">
                {latestJob ? latestJob.status : "Sin ejecuciones registradas"}
              </p>
              {latestJob?.error ? (
                <p className="mt-2 text-sm text-red-600">{latestJob.error}</p>
              ) : null}
            </article>

            <article className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Resultados guardados
              </p>
              <p className="mt-2 text-sm text-slate-800">{results.length}</p>
            </article>
          </div>
          {!canGenerate ? (
            <p className="mt-4 text-sm text-amber-700">
              Aún no hay entrevistas completadas. El diagnóstico se habilita cuando exista al menos
              una entrevista enviada.
            </p>
          ) : null}
        </section>

        {results.length === 0 ? (
          <section className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-8 text-slate-600">
            <h2 className="text-xl font-semibold text-slate-900">Aún no hay diagnóstico</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6">
              Completa al menos una entrevista y usa el botón de procesamiento para generar la
              primera lectura diagnóstica del caso.
            </p>
          </section>
        ) : (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Último resultado disponible</p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                {formatResultType(results[0].type)}
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                Generado el{" "}
                {new Intl.DateTimeFormat("es-CO", {
                  dateStyle: "medium",
                  timeStyle: "short",
                }).format(new Date(results[0].created_at))}
              </p>

              <div className="mt-6 grid gap-4">
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Resumen ejecutivo
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {stringifyValue(results[0].result?.resumen_ejecutivo)}
                  </p>
                </article>
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Lectura general
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {stringifyValue(results[0].result?.lectura_general)}
                  </p>
                </article>
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Hallazgos clave
                  </p>
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-6 text-slate-700">
                    {stringifyValue(results[0].result?.hallazgos_clave)}
                  </pre>
                </article>
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Riesgos principales
                  </p>
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-6 text-slate-700">
                    {stringifyValue(results[0].result?.riesgos_principales)}
                  </pre>
                </article>
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Recomendaciones
                  </p>
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-6 text-slate-700">
                    {stringifyValue(results[0].result?.recomendaciones)}
                  </pre>
                </article>
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Contexto estratégico
                  </p>
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-6 text-slate-700">
                    {stringifyValue(results[0].result?.contexto_estrategico)}
                  </pre>
                </article>
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Scores
                  </p>
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-6 text-slate-700">
                    {stringifyValue(results[0].result?.scores)}
                  </pre>
                </article>
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Metadata
                  </p>
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-6 text-slate-700">
                    {stringifyValue(results[0].result?.metadata)}
                  </pre>
                </article>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-900">Historial</h2>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50 text-left text-slate-600">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Tipo</th>
                      <th className="px-4 py-3 font-semibold">Grupo</th>
                      <th className="px-4 py-3 font-semibold">Fecha</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {results.map((result) => (
                      <tr key={result.id} className="text-slate-700">
                        <td className="px-4 py-3">{formatResultType(result.type)}</td>
                        <td className="px-4 py-3">{result.group_id ?? "General"}</td>
                        <td className="px-4 py-3">
                          {new Intl.DateTimeFormat("es-CO", {
                            dateStyle: "medium",
                            timeStyle: "short",
                          }).format(new Date(result.created_at))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </main>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Error inesperado";

    if (message === "UNAUTHORIZED") {
      redirect("/login");
    }

    return (
      <main className="p-6 md:p-8">
        <p className="text-red-600">{message}</p>
      </main>
    );
  }
}
