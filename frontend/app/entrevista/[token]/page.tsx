"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

type QuestionType = "abierta" | "escala_5";

type InterviewQuestion = {
  id: string;
  lente: string;
  texto: string;
  tipo: QuestionType;
};

type TokenStatus = "pending" | "in_progress" | "completed" | "expired";
type ViewState = "loading" | "ready" | "invalid" | "expired" | "completed" | "success" | "error";

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

function isResponseComplete(answers: Record<string, string>) {
  return QUESTIONS.every((question) => answers[question.id]?.trim());
}

export default function PublicInterviewPage() {
  const params = useParams<{ token: string }>();
  const token = typeof params?.token === "string" ? params.token : "";

  const [viewState, setViewState] = useState<ViewState>("loading");
  const [interview, setInterview] = useState<PublicInterviewResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>(() => normalizeAnswers({}));
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
        setInterview(payload);
        setAnswers(normalizeAnswers(payload.data));

        if (payload.token_status === "expired") {
          setViewState("expired");
          return;
        }

        if (payload.token_status === "completed") {
          setViewState("completed");
          return;
        }

        setViewState("ready");
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

  const completedCount = useMemo(
    () => QUESTIONS.filter((question) => answers[question.id]?.trim()).length,
    [answers],
  );

  const canSubmit = isResponseComplete(answers) && !submitting;

  const handleTextChange = (questionId: string, value: string) => {
    setAnswers((current) => ({
      ...current,
      [questionId]: value,
    }));
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
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError(payload?.detail ?? "Esta entrevista ya fue completada.");
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
      <main style={styles.main}>
        <section style={styles.card}>
          <h1 style={styles.title}>Cargando entrevista...</h1>
          <p style={styles.text}>Estamos validando tu enlace.</p>
        </section>
      </main>
    );
  }

  if (viewState === "invalid") {
    return (
      <main style={styles.main}>
        <section style={styles.card}>
          <h1 style={styles.title}>Enlace inválido</h1>
          <p style={styles.text}>Este enlace no es válido o ya no está disponible.</p>
        </section>
      </main>
    );
  }

  if (viewState === "expired") {
    return (
      <main style={styles.main}>
        <section style={styles.card}>
          <h1 style={styles.title}>Enlace expirado</h1>
          <p style={styles.text}>Este enlace expiró. Contacta a tu organización para recibir una nueva invitación.</p>
        </section>
      </main>
    );
  }

  if (viewState === "completed") {
    return (
      <main style={styles.main}>
        <section style={styles.card}>
          <h1 style={styles.title}>Entrevista completada</h1>
          <p style={styles.text}>Ya registramos tus respuestas. Gracias por compartir tu perspectiva.</p>
          {error ? (
            <p role="alert" style={styles.error}>
              {error}
            </p>
          ) : null}
        </section>
      </main>
    );
  }

  if (viewState === "success") {
    return (
      <main style={styles.main}>
        <section style={styles.card}>
          <h1 style={styles.title}>Respuestas enviadas</h1>
          <p style={styles.text}>Tu entrevista fue enviada exitosamente. Gracias por tu tiempo.</p>
          {interview?.submitted_at ? (
            <p style={styles.meta}>Enviada el {new Date(interview.submitted_at).toLocaleString("es-CO")}.</p>
          ) : null}
        </section>
      </main>
    );
  }

  if (viewState === "error") {
    return (
      <main style={styles.main}>
        <section style={styles.card}>
          <h1 style={styles.title}>No se pudo cargar la entrevista</h1>
          <p style={styles.text}>{error ?? "Intenta nuevamente en unos minutos."}</p>
        </section>
      </main>
    );
  }

  return (
    <main style={styles.main}>
      <section style={styles.card}>
        <header style={styles.header}>
          <div>
            <p style={styles.eyebrow}>Entrevista organizacional</p>
            <h1 style={styles.title}>{interview?.name ?? "Entrevista"}</h1>
            <p style={styles.text}>{interview?.role_label ?? "Participante"}</p>
          </div>
          <p style={styles.progress}>
            {completedCount} de {QUESTIONS.length} respondidas
          </p>
        </header>

        <p style={styles.text}>
          Tus respuestas se usarán de forma agregada. Completa las 15 preguntas antes de enviar la entrevista.
        </p>

        {error ? (
          <p role="alert" style={styles.error}>
            {error}
          </p>
        ) : null}

        <form onSubmit={handleSubmit} style={styles.form}>
          {QUESTIONS.map((question, index) => (
            <fieldset key={question.id} style={styles.fieldset}>
              <legend style={styles.legend}>
                {index + 1}. {question.texto}
              </legend>
              <p style={styles.meta}>Lente: {question.lente}</p>

              {question.tipo === "escala_5" ? (
                <div style={styles.scaleRow}>
                  {SCALE_OPTIONS.map((option) => (
                    <label key={option} style={styles.scaleOption}>
                      <input
                        type="radio"
                        name={question.id}
                        value={option}
                        checked={answers[question.id] === String(option)}
                        onChange={(event) => handleTextChange(question.id, event.target.value)}
                      />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <textarea
                  name={question.id}
                  value={answers[question.id] ?? ""}
                  onChange={(event) => handleTextChange(question.id, event.target.value)}
                  rows={5}
                  style={styles.textarea}
                />
              )}
            </fieldset>
          ))}

          <button type="submit" disabled={!canSubmit} style={styles.button}>
            {submitting ? "Enviando..." : "Enviar respuestas"}
          </button>
        </form>
      </section>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  main: {
    background: "#f5f7fb",
    minHeight: "100vh",
    padding: "32px 16px",
  },
  card: {
    background: "#ffffff",
    border: "1px solid #d8dee8",
    borderRadius: 16,
    margin: "0 auto",
    maxWidth: 860,
    padding: 24,
  },
  header: {
    alignItems: "flex-start",
    display: "flex",
    gap: 16,
    justifyContent: "space-between",
    marginBottom: 16,
  },
  eyebrow: {
    color: "#5b6472",
    fontSize: 14,
    margin: "0 0 6px",
    textTransform: "uppercase",
  },
  title: {
    color: "#172033",
    fontSize: 30,
    lineHeight: 1.1,
    margin: "0 0 8px",
  },
  text: {
    color: "#3f4a5a",
    lineHeight: 1.5,
    margin: 0,
  },
  meta: {
    color: "#667085",
    fontSize: 14,
    margin: "6px 0 0",
  },
  progress: {
    color: "#172033",
    fontSize: 14,
    fontWeight: 600,
    margin: 0,
    whiteSpace: "nowrap",
  },
  form: {
    display: "grid",
    gap: 16,
    marginTop: 24,
  },
  fieldset: {
    border: "1px solid #d8dee8",
    borderRadius: 12,
    margin: 0,
    padding: 16,
  },
  legend: {
    color: "#172033",
    fontSize: 16,
    fontWeight: 600,
    padding: "0 8px",
  },
  scaleRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 12,
    marginTop: 12,
  },
  scaleOption: {
    alignItems: "center",
    display: "inline-flex",
    gap: 6,
  },
  textarea: {
    border: "1px solid #c7d0dd",
    borderRadius: 10,
    boxSizing: "border-box",
    font: "inherit",
    marginTop: 12,
    minHeight: 120,
    padding: 12,
    resize: "vertical",
    width: "100%",
  },
  button: {
    background: "#172033",
    border: "none",
    borderRadius: 10,
    color: "#ffffff",
    cursor: "pointer",
    fontSize: 16,
    fontWeight: 600,
    padding: "14px 18px",
  },
  error: {
    color: "#b42318",
    margin: "16px 0 0",
  },
};
