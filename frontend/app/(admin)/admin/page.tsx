import Link from "next/link";
import { redirect } from "next/navigation";

import { getSessionPayload } from "@/lib/session";
import { serverFetch } from "@/lib/serverFetch";

type DashboardPendingInterview = {
  member_id: string;
  member_name: string;
  role_label: string;
  group_id: string | null;
  token_status: "pending" | "in_progress" | "completed" | "expired";
};

type DashboardLatestResult = {
  id: string;
  type: string;
  created_at: string;
};

type DashboardResponse = {
  organization: {
    id: string;
    name: string;
    description: string;
    sector: string;
  };
  total_members: number;
  total_groups: number;
  completed_interviews: number;
  in_progress_interviews: number;
  pending_interviews: number;
  completion_pct: number;
  pending_actions: string[];
  pending_interviews_list: DashboardPendingInterview[];
  can_generate_diagnosis: boolean;
  latest_result: DashboardLatestResult | null;
  latest_job: {
    id: string;
    status: string;
    error: string | null;
    created_at: string;
    updated_at: string;
  } | null;
};

function formatResultType(type: string) {
  if (type === "orientado") {
    return "Reporte orientado";
  }

  if (type === "ciego") {
    return "Reporte ciego";
  }

  return "Resultado";
}

function formatStatus(status: DashboardPendingInterview["token_status"]) {
  if (status === "in_progress") {
    return "En progreso";
  }

  if (status === "completed") {
    return "Completada";
  }

  if (status === "expired") {
    return "Expirada";
  }

  return "Pendiente";
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Ocurrió un error inesperado";
}

export default async function AdminPage() {
  try {
    const session = await getSessionPayload();

    if (!session || !session.organization_id) {
      redirect("/login");
    }

    const dashboard = await serverFetch<DashboardResponse>(
      `/organizations/${session.organization_id}/dashboard`
    );

    return (
      <section className="space-y-8 p-6 md:p-8">
        <header className="rounded-3xl bg-slate-950 px-6 py-8 text-white">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
            Resumen del caso
          </p>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">
            {dashboard.organization.name}
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300 md:text-base">
            {dashboard.organization.description?.trim()
              ? dashboard.organization.description
              : "Esta vista concentra el estado del levantamiento, los pendientes operativos y el acceso directo al diagnóstico."}
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm text-slate-300">
            <span className="rounded-full border border-slate-700 px-3 py-1">
              Sector: {dashboard.organization.sector || "Sin definir"}
            </span>
            <span className="rounded-full border border-slate-700 px-3 py-1">
              Cobertura: {dashboard.completion_pct}%
            </span>
          </div>
        </header>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm text-slate-500">Estructura</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{dashboard.total_groups}</p>
            <p className="mt-2 text-sm text-slate-600">grupos creados para ordenar el caso</p>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm text-slate-500">Personas</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{dashboard.total_members}</p>
            <p className="mt-2 text-sm text-slate-600">miembros cargados en la organización</p>
          </article>

          <article className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
            <p className="text-sm text-emerald-700">Entrevistas completadas</p>
            <p className="mt-2 text-3xl font-semibold text-emerald-950">
              {dashboard.completed_interviews}
            </p>
            <p className="mt-2 text-sm text-emerald-800">respuestas ya disponibles para lectura</p>
          </article>

          <article className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
            <p className="text-sm text-amber-700">Pendientes o en curso</p>
            <p className="mt-2 text-3xl font-semibold text-amber-950">
              {dashboard.pending_interviews + dashboard.in_progress_interviews}
            </p>
            <p className="mt-2 text-sm text-amber-800">
              {dashboard.pending_interviews} pendientes y {dashboard.in_progress_interviews} en progreso
            </p>
          </article>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-3xl border border-slate-200 bg-white p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Qué sigue</h2>
                <p className="mt-1 text-sm text-slate-600">
                  El producto debe dejar claro el siguiente paso para llegar al diagnóstico.
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-slate-500">Progreso total</p>
                <p className="text-2xl font-semibold text-slate-900">{dashboard.completion_pct}%</p>
              </div>
            </div>

            <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-slate-900"
                style={{ width: `${dashboard.completion_pct}%` }}
              />
            </div>

            <div className="mt-6 space-y-3">
              {dashboard.pending_actions.length > 0 ? (
                dashboard.pending_actions.map((action) => (
                  <article
                    key={action}
                    className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
                  >
                    {action}
                  </article>
                ))
              ) : (
                <article className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                  El caso ya tiene estructura, personas, entrevistas y resultados básicos disponibles.
                </article>
              )}
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/groups"
                className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
              >
                Ir a estructura
              </Link>
              <Link
                href="/members"
                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Gestionar personas
              </Link>
              <Link
                href="/interviews"
                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Revisar entrevistas
              </Link>
              <Link
                href="/results"
                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Ver resultados
              </Link>
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6">
            <h2 className="text-xl font-semibold text-slate-900">Resultados</h2>
            <p className="mt-1 text-sm text-slate-600">
              Estado actual del diagnóstico disponible para esta organización.
            </p>

            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Último procesamiento
              </p>
              <p className="mt-2 text-sm text-slate-700">
                {dashboard.latest_job ? dashboard.latest_job.status : "Sin ejecuciones registradas"}
              </p>
              {dashboard.latest_job?.error ? (
                <p className="mt-2 text-sm text-red-600">{dashboard.latest_job.error}</p>
              ) : null}
            </div>

            {dashboard.latest_result ? (
              <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-sm font-medium text-emerald-800">
                  {formatResultType(dashboard.latest_result.type)}
                </p>
                <p className="mt-2 text-sm text-emerald-950">
                  Última generación registrada:{" "}
                  {new Intl.DateTimeFormat("es-CO", {
                    dateStyle: "medium",
                    timeStyle: "short",
                  }).format(new Date(dashboard.latest_result.created_at))}
                </p>
                <Link
                  href="/results"
                  className="mt-4 inline-flex rounded-xl bg-emerald-900 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
                >
                  Abrir resultados
                </Link>
              </div>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
                Todavía no hay resultados guardados.{" "}
                {dashboard.can_generate_diagnosis
                  ? "Ya puedes generar un diagnóstico desde la sección Resultados."
                  : "Primero completa al menos una entrevista para habilitar el diagnóstico."}
              </div>
            )}
          </section>
        </div>

        <section className="rounded-3xl border border-slate-200 bg-white p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Entrevistas a completar</h2>
              <p className="mt-1 text-sm text-slate-600">
                Seguimiento operativo de los miembros que todavía no han terminado su entrevista.
              </p>
            </div>
            <Link href="/interviews" className="text-sm font-medium text-slate-700 hover:text-slate-950">
              Ver todas
            </Link>
          </div>

          {dashboard.pending_interviews_list.length === 0 ? (
            <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
              No hay entrevistas pendientes visibles en este momento.
            </div>
          ) : (
            <div className="mt-5 grid gap-3">
              {dashboard.pending_interviews_list.map((item) => (
                <article
                  key={item.member_id}
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
                >
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="font-medium text-slate-900">{item.member_name}</p>
                      <p className="text-sm text-slate-600">
                        {item.role_label || "Sin rol definido"}
                        {item.group_id ? ` · Grupo ${item.group_id}` : ""}
                      </p>
                    </div>
                    <span className="rounded-full border border-slate-300 px-3 py-1 text-xs font-medium uppercase tracking-wide text-slate-700">
                      {formatStatus(item.token_status)}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </section>
    );
  } catch (error: unknown) {
    return <p className="p-6 text-red-600">{getErrorMessage(error)}</p>;
  }
}
