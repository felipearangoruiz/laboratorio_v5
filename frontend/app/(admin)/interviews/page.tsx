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
  {
    id: "q01",
    texto:
      "¿Quién crees que toma las decisiones más importantes en esta organización? No tiene que ser la persona con el cargo más alto.",
  },
  {
    id: "q02",
    texto:
      "¿Qué tan accesible es la dirección para resolver problemas operativos del día a día? (1=Nada accesible, 5=Muy accesible)",
  },
  {
    id: "q03",
    texto:
      "¿Hay alguien cuya aprobación o visto bueno es necesario para que las cosas avancen, aunque no sea su responsabilidad formal?",
  },
  {
    id: "q04",
    texto:
      "Describe un proceso de tu trabajo diario que sientes que podría ser más rápido o más simple. ¿Dónde se detiene o complica?",
  },
  {
    id: "q05",
    texto:
      "¿Con qué frecuencia tienes que esperar a otra persona o área para poder avanzar en tu trabajo? (1=Casi nunca, 5=Casi siempre)",
  },
  {
    id: "q06",
    texto: "¿Cuándo fue la última vez que un proceso no funcionó como se esperaba? ¿Qué pasó?",
  },
  {
    id: "q07",
    texto:
      "¿Hay reglas o procedimientos formales que en la práctica nadie sigue? ¿Por qué crees que es así?",
  },
  {
    id: "q08",
    texto:
      "¿Hay cosas que 'todos saben que se hacen así' aunque no estén escritas en ningún lado? ¿Cuál es la más importante?",
  },
  {
    id: "q09",
    texto:
      "¿Qué tan claras son las reglas sobre quién puede tomar qué decisiones? (1=Muy confusas, 5=Muy claras)",
  },
  {
    id: "q10",
    texto:
      "¿Qué comportamientos o resultados son los que realmente se reconocen o recompensan aquí, aunque no sean los declarados oficialmente?",
  },
  {
    id: "q11",
    texto:
      "¿Hay situaciones en las que hacer lo correcto para la organización va en contra de lo que te conviene a ti personalmente? ¿Puedes dar un ejemplo?",
  },
  {
    id: "q12",
    texto:
      "¿Sientes que tu esfuerzo y contribución se reconocen de forma justa? (1=Para nada, 5=Completamente)",
  },
  {
    id: "q13",
    texto:
      "Describe una situación reciente (últimos 6 meses) en la que algo salió bien gracias a cómo está organizado el trabajo aquí.",
  },
  {
    id: "q14",
    texto:
      "Describe una situación reciente en la que algo salió mal o generó fricción innecesaria. ¿Qué lo causó?",
  },
  {
    id: "q15",
    texto:
      "Si pudieras cambiar una sola cosa de cómo funciona esta organización, ¿qué cambiarías y por qué?",
  },
];

const questionsById = new Map(QUESTIONS.map((question) => [question.id, question.texto]));

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

function formatDate(value: string | null): string {
  if (!value) {
    return "Sin respuesta";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Sin respuesta";
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

    return (
      <main className="space-y-6 p-6 md:p-8">
        <header className="space-y-2">
          <h1 className="text-2xl font-bold text-slate-900 md:text-3xl">Entrevistas</h1>
          <p className="max-w-3xl text-sm text-slate-600 md:text-base">
            Revisa el estado de entrevistas por miembro y consulta las respuestas enviadas.
          </p>
        </header>

        {interviews.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-slate-600">
            No hay entrevistas registradas para esta organización.
          </p>
        ) : (
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-slate-600">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Miembro</th>
                    <th className="px-4 py-3 font-semibold">Rol</th>
                    <th className="px-4 py-3 font-semibold">Estado</th>
                    <th className="px-4 py-3 font-semibold">Entrevista</th>
                    <th className="px-4 py-3 font-semibold">Fecha</th>
                    <th className="px-4 py-3 font-semibold">Detalle</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {interviews.map((item) => {
                    const hasAnswers =
                      Boolean(item.interview_id) && Object.keys(item.answers ?? {}).length > 0;

                    return (
                      <tr key={item.member_id} className="align-top text-slate-700">
                        <td className="px-4 py-4">
                          <div className="font-medium text-slate-900">{item.member_name}</div>
                          <div className="text-xs text-slate-500">{item.member_id}</div>
                        </td>
                        <td className="px-4 py-4">{item.role_label || "Sin rol"}</td>
                        <td className="px-4 py-4">{formatTokenStatus(item.token_status)}</td>
                        <td className="px-4 py-4">{item.interview_id ? "Sí" : "No"}</td>
                        <td className="px-4 py-4">{formatDate(item.submitted_at)}</td>
                        <td className="px-4 py-4">
                          {hasAnswers ? (
                            <details className="group max-w-xl">
                              <summary className="cursor-pointer list-none rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50">
                                Ver respuestas
                              </summary>
                              <div className="mt-3 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                                {QUESTIONS.map((question) => (
                                  <div key={question.id} className="space-y-1">
                                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                      {question.id}
                                    </p>
                                    <p className="font-medium text-slate-800">
                                      {questionsById.get(question.id) ?? question.texto}
                                    </p>
                                    <p className="whitespace-pre-wrap text-slate-700">
                                      {normalizeAnswer(item.answers?.[question.id])}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </details>
                          ) : (
                            <span className="text-slate-500">Sin respuesta</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
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
