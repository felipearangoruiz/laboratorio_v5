"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";

type QuestionType = "abierta" | "escala_5";

type InterviewQuestion = {
  id: string;
  lente: string;
  texto: string;
  tipo: QuestionType;
};

type TokenStatus = "pending" | "in_progress" | "completed" | "expired";
type ViewState =
  | "loading"
  | "intro"
  | "ready"
  | "review"
  | "invalid"
  | "expired"
  | "completed"
  | "success"
  | "error";

type PublicInterviewResponse = {
  member_id: string;
  name: string;
  role_label: string;
  token_status: TokenStatus;
  submitted_at: string | null;
  schema_version: number;
  data: Record<string, unknown>;
};

const QUESTIONS: InterviewQuestion[] = [
  {
    id: "q01",
    lente: "actores",
    texto: "¿Quién crees que toma las decisiones más importantes en esta organización? No tiene que ser la persona con el cargo más alto.",
    tipo: "abierta",
  },
  {
    id: "q02",
    lente: "actores",
    texto: "¿Qué tan accesible es la dirección para resolver problemas operativos del día a día? (1=Nada accesible, 5=Muy accesible)",
    tipo: "escala_5",
  },
  {
    id: "q03",
    lente: "actores",
    texto: "¿Hay alguien cuya aprobación o visto bueno es necesario para que las cosas avancen, aunque no sea su responsabilidad formal?",
    tipo: "abierta",
  },
  {
    id: "q04",
    lente: "procesos",
    texto: "Describe un proceso de tu trabajo diario que sientes que podría ser más rápido o más simple. ¿Dónde se detiene o complica?",
    tipo: "abierta",
  },
  {
    id: "q05",
    lente: "procesos",
    texto: "¿Con qué frecuencia tienes que esperar a otra persona o área para poder avanzar en tu trabajo? (1=Casi nunca, 5=Casi siempre)",
    tipo: "escala_5",
  },
  {
    id: "q06",
    lente: "procesos",
    texto: "¿Cuándo fue la última vez que un proceso no funcionó como se esperaba? ¿Qué pasó?",
    tipo: "abierta",
  },
  {
    id: "q07",
    lente: "reglas",
    texto: "¿Hay reglas o procedimientos formales que en la práctica nadie sigue? ¿Por qué crees que es así?",
    tipo: "abierta",
  },
  {
    id: "q08",
    lente: "reglas",
    texto: "¿Hay cosas que 'todos saben que se hacen así' aunque no estén escritas en ningún lado? ¿Cuál es la más importante?",
    tipo: "abierta",
  },
  {
    id: "q09",
    lente: "reglas",
    texto: "¿Qué tan claras son las reglas sobre quién puede tomar qué decisiones? (1=Muy confusas, 5=Muy claras)",
    tipo: "escala_5",
  },
  {
    id: "q10",
    lente: "incentivos",
    texto: "¿Qué comportamientos o resultados son los que realmente se reconocen o recompensan aquí, aunque no sean los declarados oficialmente?",
    tipo: "abierta",
  },
  {
    id: "q11",
    lente: "incentivos",
    texto: "¿Hay situaciones en las que hacer lo correcto para la organización va en contra de lo que te conviene a ti personalmente? ¿Puedes dar un ejemplo?",
    tipo: "abierta",
  },
  {
    id: "q12",
    lente: "incentivos",
    texto: "¿Sientes que tu esfuerzo y contribución se reconocen de forma justa? (1=Para nada, 5=Completamente)",
    tipo: "escala_5",
  },
  {
    id: "q13",
    lente: "episodios",
    texto: "Describe una situación reciente (últimos 6 meses) en la que algo salió bien gracias a cómo está organizado el trabajo aquí.",
    tipo: "abierta",
  },
  {
    id: "q14",
    lente: "episodios",
    texto: "Describe una situación reciente en la que algo salió mal o generó fricción innecesaria. ¿Qué lo causó?",
    tipo: "abierta",
  },
  {
    id: "q15",
    lente: "episodios",
    texto: "Si pudieras cambiar una sola cosa de cómo funciona esta organización, ¿qué cambiarías y por qué?",
    tipo: "abierta",
  },
];

const SCALE_OPTIONS = [1, 2, 3, 4, 5];

function getApiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Ocurrió un error al cargar la entrevista.";
}

function normalizeAnswers(data: Record<string, unknown>) {
  const nextAnswers: Record<string, string> = {};

  for (const question of QUESTIONS) {
    const value = data[question.id];
    nextAnswers[question.id] = value == null ? "" : String(value);
  }

  return nextAnswers;
}

function getFirstIncompleteStep(answers: Record<string, string>) {
  const index = QUESTIONS.findIndex((question) => !answers[question.id]?.trim());
  return index === -1 ? QUESTIONS.length - 1 : index;
}

function isResponseComplete(answers: Record<string, string>) {
  return QUESTIONS.every((question) => answers[question.id]?.trim());
}

export default function PublicInterviewPage() {
  const params = useParams<{ token: string }>();
  const token = typeof params?.token === "string" ? params.token : "";

  const [viewState, setViewState] = useState<ViewState>("loading");
  const [interview, setInterview] = useState<PublicInterviewResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>(() => normalizeAnswers({}));
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [draftSaving, setDraftSaving] = useState(false);
  const [draftSavedAt, setDraftSavedAt] = useState<string | null>(null);
  const hasLoadedRef = useRef(false);

  useEffect(() => {
    if (!token) {
      setViewState("invalid");
      return;
    }

    let cancelled = false;

    async function loadInterview() {
      setViewState("loading");
      setError(null);

      try {
        const response = await fetch(`${getApiBaseUrl()}/entrevista/${encodeURIComponent(token)}`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
          cache: "no-store",
        });

        if (cancelled) {
          return;
        }

        if (response.status === 404) {
          setViewState("invalid");
          return;
        }

        if (response.status === 410) {
          setViewState("expired");
          return;
        }

        if (!response.ok) {
          throw new Error("No se pudo cargar la entrevista.");
        }

        const payload = (await response.json()) as PublicInterviewResponse;
        const normalizedAnswers = normalizeAnswers(payload.data);
        setInterview(payload);
        setAnswers(normalizedAnswers);
        setStep(getFirstIncompleteStep(normalizedAnswers));
        hasLoadedRef.current = true;

        if (payload.token_status === "expired") {
          setViewState("expired");
          return;
        }

        if (payload.token_status === "completed") {
          setViewState("completed");
          return;
        }

        setViewState("intro");
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        setError(getErrorMessage(loadError));
        setViewState("error");
      }
    }

    void loadInterview();

    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token || !hasLoadedRef.current) {
      return;
    }

    if (viewState !== "ready" && viewState !== "review") {
      return;
    }

    const timeout = window.setTimeout(async () => {
      try {
        setDraftSaving(true);
        const response = await fetch(`${getApiBaseUrl()}/entrevista/${encodeURIComponent(token)}/draft`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ data: answers }),
        });

        if (!response.ok) {
          throw new Error("No se pudo guardar el avance.");
        }

        setDraftSavedAt(new Date().toISOString());
      } catch (draftError) {
        setError(getErrorMessage(draftError));
      } finally {
        setDraftSaving(false);
      }
    }, 900);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [answers, token, viewState]);

  const completedCount = useMemo(
    () => QUESTIONS.filter((question) => answers[question.id]?.trim()).length,
    [answers]
  );

  const canSubmit = isResponseComplete(answers) && !submitting;
  const currentQuestion = QUESTIONS[step];
  const progress = Math.round((completedCount / QUESTIONS.length) * 100);

  const handleTextChange = (questionId: string, value: string) => {
    setAnswers((current) => ({
      ...current,
      [questionId]: value,
    }));
  };

  const handleNext = () => {
    if (step >= QUESTIONS.length - 1) {
      setViewState("review");
      return;
    }

    setStep((current) => Math.min(current + 1, QUESTIONS.length - 1));
  };

  const handlePrevious = () => {
    setStep((current) => Math.max(current - 1, 0));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!token || !canSubmit) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${getApiBaseUrl()}/entrevista/${encodeURIComponent(token)}/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ data: answers }),
      });

      if (response.status === 404) {
        setViewState("invalid");
        return;
      }

      if (response.status === 410) {
        setViewState("expired");
        return;
      }

      if (response.status === 409) {
        setViewState("completed");
        return;
      }

      if (!response.ok) {
        throw new Error("No se pudo enviar la entrevista.");
      }

      const payload = (await response.json()) as PublicInterviewResponse;
      setInterview(payload);
      setViewState("success");
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  };

  if (viewState === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-white">
        <p className="text-sm text-slate-300">Cargando entrevista...</p>
      </main>
    );
  }

  if (viewState === "invalid") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
        <div className="max-w-xl rounded-3xl bg-white p-8 text-slate-900 shadow-xl">
          <h1 className="text-2xl font-semibold">Este enlace no es válido</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Verifica que el enlace sea correcto o vuelve a pedir acceso a tu organización.
          </p>
        </div>
      </main>
    );
  }

  if (viewState === "expired") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
        <div className="max-w-xl rounded-3xl bg-white p-8 text-slate-900 shadow-xl">
          <h1 className="text-2xl font-semibold">Este enlace expiró</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Contacta a tu organización para recibir un nuevo acceso a la entrevista.
          </p>
        </div>
      </main>
    );
  }

  if (viewState === "completed" || viewState === "success") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
        <div className="max-w-2xl rounded-[2rem] bg-white p-8 text-slate-900 shadow-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-600">
            Entrevista registrada
          </p>
          <h1 className="mt-3 text-3xl font-semibold">Tu aporte quedó guardado</h1>
          <p className="mt-4 text-sm leading-7 text-slate-600 md:text-base">
            Gracias por completar la entrevista. Tu respuesta ya fue registrada y no necesitas hacer
            ninguna acción adicional.
          </p>
        </div>
      </main>
    );
  }

  if (viewState === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
        <div className="max-w-2xl rounded-[2rem] bg-white p-8 text-slate-900 shadow-2xl">
          <h1 className="text-2xl font-semibold">Hubo un problema</h1>
          <p className="mt-3 text-sm leading-6 text-red-600">{error ?? "No se pudo continuar."}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-slate-900 md:px-6">
      <div className="mx-auto max-w-4xl">
        <div className="overflow-hidden rounded-[2rem] bg-white shadow-2xl">
          <div className="bg-slate-950 px-6 py-8 text-white md:px-8">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              Entrevista organizacional
            </p>
            <h1 className="mt-3 text-3xl font-semibold md:text-4xl">
              {viewState === "intro" ? "Tu lectura del funcionamiento real" : "Avance de entrevista"}
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300 md:text-base">
              Esta entrevista busca entender cómo funciona realmente la organización. Tus respuestas
              se guardan a medida que avanzas y podrás retomarlas con este mismo enlace.
            </p>
          </div>

          <div className="space-y-6 px-6 py-8 md:px-8">
            <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Rol: {interview?.role_label || "Sin rol definido"}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Progreso: {completedCount}/{QUESTIONS.length}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                {draftSaving
                  ? "Guardando avance..."
                  : draftSavedAt
                    ? `Guardado ${new Intl.DateTimeFormat("es-CO", {
                        timeStyle: "short",
                      }).format(new Date(draftSavedAt))}`
                    : "Aún no hay avance guardado"}
              </span>
            </div>

            <div className="h-3 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-slate-900" style={{ width: `${progress}%` }} />
            </div>

            {viewState === "intro" ? (
              <section className="space-y-5">
                <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
                  <h2 className="text-xl font-semibold text-slate-900">Antes de empezar</h2>
                  <div className="mt-4 grid gap-3 text-sm leading-6 text-slate-700">
                    <p>1. La entrevista toma entre 10 y 15 minutos.</p>
                    <p>2. Las respuestas se guardan automáticamente mientras avanzas.</p>
                    <p>3. Al final podrás revisar todo antes de enviar definitivamente.</p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setViewState("ready")}
                  className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-800"
                >
                  Empezar entrevista
                </button>
              </section>
            ) : null}

            {viewState === "ready" && currentQuestion ? (
              <section className="space-y-6">
                <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
                    Pregunta {step + 1} de {QUESTIONS.length}
                  </p>
                  <p className="mt-2 text-sm font-medium uppercase tracking-wide text-slate-500">
                    Lente: {currentQuestion.lente}
                  </p>
                  <h2 className="mt-3 text-2xl font-semibold text-slate-900">
                    {currentQuestion.texto}
                  </h2>
                </div>

                {currentQuestion.tipo === "abierta" ? (
                  <textarea
                    value={answers[currentQuestion.id] ?? ""}
                    onChange={(event) => handleTextChange(currentQuestion.id, event.target.value)}
                    className="min-h-[220px] w-full rounded-3xl border border-slate-300 px-4 py-4 text-sm leading-6 text-slate-800 outline-none transition focus:border-slate-500"
                    placeholder="Escribe tu respuesta con el mayor detalle posible."
                  />
                ) : (
                  <div className="grid gap-3 md:grid-cols-5">
                    {SCALE_OPTIONS.map((option) => {
                      const selected = answers[currentQuestion.id] === String(option);

                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => handleTextChange(currentQuestion.id, String(option))}
                          className={`rounded-3xl border px-4 py-5 text-left transition ${
                            selected
                              ? "border-slate-900 bg-slate-900 text-white"
                              : "border-slate-300 bg-white text-slate-800 hover:border-slate-500"
                          }`}
                        >
                          <div className="text-2xl font-semibold">{option}</div>
                          <div className="mt-2 text-xs uppercase tracking-wide opacity-80">
                            {option === 1 ? "Muy bajo" : option === 5 ? "Muy alto" : "Intermedio"}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}

                <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
                  <button
                    type="button"
                    onClick={handlePrevious}
                    disabled={step === 0}
                    className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Anterior
                  </button>

                  <button
                    type="button"
                    onClick={handleNext}
                    className="rounded-xl bg-slate-900 px-5 py-2 text-sm font-medium text-white hover:bg-slate-800"
                  >
                    {step === QUESTIONS.length - 1 ? "Revisar antes de enviar" : "Siguiente"}
                  </button>
                </div>
              </section>
            ) : null}

            {viewState === "review" ? (
              <form onSubmit={handleSubmit} className="space-y-6">
                <section className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
                  <h2 className="text-2xl font-semibold text-slate-900">Revisa antes de enviar</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    Ya respondiste {completedCount} de {QUESTIONS.length} preguntas. El envío final
                    es irreversible.
                  </p>
                </section>

                <div className="grid gap-4">
                  {QUESTIONS.map((question, index) => (
                    <article key={question.id} className="rounded-3xl border border-slate-200 bg-white p-5">
                      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
                        Pregunta {index + 1}
                      </p>
                      <h3 className="mt-2 font-semibold text-slate-900">{question.texto}</h3>
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                        {answers[question.id]?.trim() || "Sin respuesta"}
                      </p>
                    </article>
                  ))}
                </div>

                {error ? (
                  <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {error}
                  </div>
                ) : null}

                <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
                  <button
                    type="button"
                    onClick={() => {
                      setStep(QUESTIONS.length - 1);
                      setViewState("ready");
                    }}
                    className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Volver a editar
                  </button>
                  <button
                    type="submit"
                    disabled={!canSubmit}
                    className="rounded-xl bg-emerald-700 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-emerald-300"
                  >
                    {submitting ? "Enviando..." : "Enviar respuestas"}
                  </button>
                </div>
              </form>
            ) : null}
          </div>
        </div>
      </div>
    </main>
  );
}
