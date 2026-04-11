import { redirect } from "next/navigation";

import { serverFetch } from "@/lib/serverFetch";
import { getSessionPayload } from "@/lib/session";

type TokenStatus = "pending" | "in_progress" | "completed" | "expired";

type InterviewRow = {
  member_id: string;
  member_name: string;
  role_label: string;
  group_id: string | null;
  token_status: TokenStatus;
  interview_id: string | null;
  answers: Record<string, unknown>;
  submitted_at: string | null;
};

type Question = {
  id: string;
  texto: string;
};

const QUESTIONS: Question[] = [
  { id: "q01", texto: "¿Quién crees que toma las decisiones más importantes en esta organización?" },
  { id: "q02", texto: "¿Qué tan accesible es la dirección para resolver problemas operativos del día a día?" },
  { id: "q03", texto: "¿Hay alguien cuya aprobación o visto bueno es necesario para que las cosas avancen?" },
  { id: "q04", texto: "Describe un proceso de tu trabajo diario que podría ser más rápido o más simple." },
  { id: "q05", texto: "¿Con qué frecuencia tienes que esperar a otra persona o área para poder avanzar?" },
  { id: "q06", texto: "¿Cuándo fue la última vez que un proceso no funcionó como se esperaba?" },
  { id: "q07", texto: "¿Hay reglas o procedimientos formales que en la práctica nadie sigue?" },
  { id: "q08", texto: "¿Hay cosas que todos saben que se hacen así aunque no estén escritas?" },
  { id: "q09", texto: "¿Qué tan claras son las reglas sobre quién puede tomar qué decisiones?" },
  { id: "q10", texto: "¿Qué comportamientos o resultados son los que realmente se reconocen o recompensan?" },
  { id: "q11", texto: "¿Hay situaciones en las que hacer lo correcto para la organización va en contra de lo que te conviene?" },
  { id: "q12", texto: "¿Sientes que tu esfuerzo y contribución se reconocen de forma justa?" },
  { id: "q13", texto: "Describe una situación reciente en la que algo salió bien gracias a cómo está organizado el trabajo." },
  { id: "q14", texto: "Describe una situación reciente en la que algo salió mal o generó fricción innecesaria." },
  { id: "q15", texto: "Si pudieras cambiar una sola cosa de cómo funciona esta organización, ¿qué cambiarías?" },
];

function formatTokenStatus(status: TokenStatus): string {
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

function badgeClass(status: TokenStatus): string {
  if (status === "in_progress") {
    return "border-yellow-200 bg-yellow-50 text-yellow-800";
  }
  if (status === "completed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (status === "expired") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Sin envío final";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Sin envío final";
  }

  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function normalizeAnswer(value: unknown): string {
  if (value == null) {
    return "Sin respuesta";
  }

  if (typeof value === "string") {
    return value.trim() ? value : "Sin respuesta";
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value);
}

function answeredCount(answers: Record<string, unknown>) {
  return QUESTIONS.filter((question) => {
    const value = answers?.[question.id];
    return typeof value === "number" || (typeof value === "string" && value.trim().length > 0);
  }).length;
}

export default async function AdminInterviewsPage() {
  const session = await getSessionPayload();

  if (!session) {
    redirect("/login");
  }

  if (!session.organization_id) {
    return (
      <main className="space-y-4 p-6 md:p-8">
        <h1 className="text-2xl font-bold text-slate-900">Entrevistas</h1>
        <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          No hay una organización asociada a la sesión actual.
        </p>
      </main>
    );
  }

  try {
    const interviews = await serverFetch<InterviewRow[]>(
      `/organizations/${session.organization_id}/interviews`
    );

    const pending = interviews.filter((item) => item.token_status === "pending").length;
    const inProgress = interviews.filter((item) => item.token_status === "in_progress").length;
    const completed = interviews.filter((item) => item.token_status === "completed").length;

    return (
      <main className="space-y-6 p-6 md:p-8">
        <header className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
            Entrevistas
          </p>
          <h1 className="text-3xl font-semibold text-slate-900">Seguimiento del levantamiento</h1>
          <p className="max-w-3xl text-sm leading-6 text-slate-600 md:text-base">
            Esta vista permite saber quién no ha empezado, quién va en progreso y qué respuestas ya
            están disponibles para lectura.
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-3">
          <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm text-slate-500">Pendientes</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{pending}</p>
          </article>
          <article className="rounded-2xl border border-yellow-200 bg-yellow-50 p-5">
            <p className="text-sm text-yellow-700">En progreso</p>
            <p className="mt-2 text-3xl font-semibold text-yellow-950">{inProgress}</p>
          </article>
          <article className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
            <p className="text-sm text-emerald-700">Completadas</p>
            <p className="mt-2 text-3xl font-semibold text-emerald-950">{completed}</p>
          </article>
        </div>

        {interviews.length === 0 ? (
          <p className="rounded-3xl border border-dashed border-slate-300 bg-white p-6 text-slate-600">
            No hay entrevistas registradas para esta organización.
          </p>
        ) : (
          <section className="space-y-4">
            {interviews.map((item) => {
              const totalAnswered = answeredCount(item.answers ?? {});
              const hasAnswers = totalAnswered > 0;

              return (
                <article
                  key={item.member_id}
                  className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="text-lg font-semibold text-slate-900">{item.member_name}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        {item.role_label || "Sin rol"}
                        {item.group_id ? ` · Grupo ${item.group_id}` : ""}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <span
                        className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-wide ${badgeClass(
                          item.token_status
                        )}`}
                      >
                        {formatTokenStatus(item.token_status)}
                      </span>
                      <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
                        {totalAnswered}/{QUESTIONS.length} respuestas guardadas
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <div className="rounded-2xl bg-slate-50 px-4 py-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Estado del envío
                      </p>
                      <p className="mt-1 text-sm text-slate-700">{formatDate(item.submitted_at)}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 px-4 py-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Entrevista creada
                      </p>
                      <p className="mt-1 text-sm text-slate-700">
                        {item.interview_id ? "Sí" : "Aún no"}
                      </p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 px-4 py-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Lectura rápida
                      </p>
                      <p className="mt-1 text-sm text-slate-700">
                        {hasAnswers
                          ? "Ya hay material suficiente para revisión inicial."
                          : "Todavía no hay respuestas registradas."}
                      </p>
                    </div>
                  </div>

                  {hasAnswers ? (
                    <details className="mt-4 group">
                      <summary className="cursor-pointer list-none rounded-2xl border border-slate-300 px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50">
                        Ver respuestas capturadas
                      </summary>
                      <div className="mt-3 grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        {QUESTIONS.map((question) => (
                          <article key={question.id} className="rounded-2xl bg-white p-4">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                              {question.id}
                            </p>
                            <p className="mt-1 font-medium text-slate-800">{question.texto}</p>
                            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                              {normalizeAnswer(item.answers?.[question.id])}
                            </p>
                          </article>
                        ))}
                      </div>
                    </details>
                  ) : null}
                </article>
              );
            })}
          </section>
        )}
      </main>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Error inesperado";

    if (message === "UNAUTHORIZED") {
      redirect("/login");
    }

    return (
      <main className="space-y-4 p-6 md:p-8">
        <h1 className="text-2xl font-bold text-slate-900">Entrevistas</h1>
        <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {message}
        </p>
      </main>
    );
  }
}
