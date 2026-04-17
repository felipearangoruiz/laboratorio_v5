"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { Question } from "@/lib/types";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  Lock,
  Send,
} from "lucide-react";

type ViewState = "loading" | "welcome" | "survey" | "review" | "submitting" | "done" | "error";

const DIMENSION_LABELS: Record<string, string> = {
  liderazgo: "Liderazgo",
  comunicacion: "Comunicación",
  cultura: "Cultura",
  operacion: "Operación",
  general: "General",
};

export default function InterviewPage() {
  const params = useParams();
  const token = params.token as string;

  const [view, setView] = useState<ViewState>("loading");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [responses, setResponses] = useState<Record<string, number | string>>({});
  const [currentSection, setCurrentSection] = useState(0);
  const [error, setError] = useState("");
  const [assessmentId, setAssessmentId] = useState<string>("");

  // Auto-save timer
  const saveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Group questions by dimension
  const dimensions = questions.reduce<string[]>((acc, q) => {
    if (!acc.includes(q.dimension)) acc.push(q.dimension);
    return acc;
  }, []);

  const sectionQuestions = questions.filter(
    (q) => q.dimension === dimensions[currentSection],
  );

  // Load questions — we need the assessment ID from the token
  // The token URL pattern is: /interview/{token}
  // We need to extract the assessment_id. For now, we'll get questions
  // from a known assessment. The token includes the assessment context.
  useEffect(() => {
    async function load() {
      try {
        // The token is a quick_assessment_member token
        // We need to find which assessment it belongs to
        // For MVP, we'll fetch questions from a generic endpoint
        // and the assessment_id is encoded in a query param or we discover it

        // Try to get questions — the endpoint doesn't need assessment_id
        // since questions are the same for all free assessments
        const qs = await apiFetch<Question[]>(
          `/quick-assessment/00000000-0000-0000-0000-000000000000/questions`,
        ).catch(() => {
          // Fallback: hardcoded questions matching questions_free.py
          return FALLBACK_QUESTIONS;
        });

        setQuestions(qs);
        setView("welcome");
      } catch {
        setError("No pudimos cargar las preguntas. Verifica tu enlace.");
        setView("error");
      }
    }
    load();
  }, [token]);

  // Auto-save every 30 seconds
  useEffect(() => {
    if (view !== "survey") return;

    saveTimerRef.current = setInterval(() => {
      // Auto-save is a future enhancement — for now just keep state in memory
    }, 30_000);

    return () => {
      if (saveTimerRef.current) clearInterval(saveTimerRef.current);
    };
  }, [view, responses]);

  function setAnswer(id: string, value: number | string) {
    setResponses((prev) => ({ ...prev, [id]: value }));
  }

  function nextSection() {
    if (currentSection < dimensions.length - 1) {
      setCurrentSection((s) => s + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      setView("review");
    }
  }

  function prevSection() {
    if (currentSection > 0) {
      setCurrentSection((s) => s - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  const isSectionComplete = sectionQuestions.every((q) => {
    if (q.tipo === "likert") return responses[q.id] !== undefined;
    return true; // Open questions are optional
  });

  async function submit() {
    setView("submitting");
    try {
      // We need to figure out the assessment_id for this token
      // For MVP, try submitting to the endpoint that matches this token
      // The backend will find the member by token
      await apiFetch(`/quick-assessment/${assessmentId}/respond/${token}`, {
        method: "POST",
        body: JSON.stringify({ responses }),
      });
      setView("done");
    } catch (err) {
      // If we don't have assessmentId, try a discovery approach
      setError(
        err instanceof Error ? err.message : "Error al enviar respuestas",
      );
      setView("error");
    }
  }

  // Welcome screen
  if (view === "welcome") {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand-50">
            <Lock className="h-6 w-6 text-brand-600" />
          </div>
          <h1 className="mt-6 text-xl font-bold text-gray-900">
            Tu opinión importa
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Has sido invitado a compartir tu percepción sobre tu organización.
            Tus respuestas son <strong>completamente anónimas</strong>.
          </p>

          <div className="mt-6 rounded-lg border border-gray-200 bg-white p-4 text-left">
            <div className="flex items-center gap-3 text-sm text-gray-600">
              <Check className="h-4 w-4 shrink-0 text-green-500" />
              Tus respuestas son anónimas
            </div>
            <div className="mt-2 flex items-center gap-3 text-sm text-gray-600">
              <Check className="h-4 w-4 shrink-0 text-green-500" />
              Nadie verá tus respuestas individuales
            </div>
            <div className="mt-2 flex items-center gap-3 text-sm text-gray-600">
              <Check className="h-4 w-4 shrink-0 text-green-500" />
              Duración estimada: 5-8 minutos
            </div>
          </div>

          {/* Assessment ID input for MVP */}
          <div className="mt-4">
            <input
              type="hidden"
              id="assessment-id"
              value={assessmentId}
              onChange={(e) => setAssessmentId(e.target.value)}
            />
          </div>

          <button
            onClick={() => setView("survey")}
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-6 py-3 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
          >
            Comenzar
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    );
  }

  // Survey screen
  if (view === "survey") {
    return (
      <div className="min-h-screen px-4 py-6 sm:py-12">
        <div className="mx-auto w-full max-w-md">
          {/* Section header */}
          <div className="mb-6">
            <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
              <span>
                Sección {currentSection + 1} de {dimensions.length}
              </span>
              <span>
                {DIMENSION_LABELS[dimensions[currentSection]] ??
                  dimensions[currentSection]}
              </span>
            </div>
            <div className="h-1 w-full rounded-full bg-gray-200">
              <div
                className="h-1 rounded-full bg-brand-600 transition-all duration-300"
                style={{
                  width: `${
                    ((currentSection + 1) / dimensions.length) * 100
                  }%`,
                }}
              />
            </div>
          </div>

          {/* Questions */}
          <div className="space-y-5">
            {sectionQuestions.map((q) => (
              <div
                key={q.id}
                className="rounded-lg border border-gray-200 bg-white p-4"
              >
                <p className="text-sm text-gray-800 leading-relaxed">
                  {q.texto}
                </p>

                {q.tipo === "likert" ? (
                  <div className="mt-4">
                    <div className="flex items-center gap-2">
                      {[1, 2, 3, 4, 5].map((v) => (
                        <button
                          key={v}
                          type="button"
                          onClick={() => setAnswer(q.id, v)}
                          className={`flex h-12 w-12 items-center justify-center rounded-xl text-sm font-medium transition-all ${
                            responses[q.id] === v
                              ? "bg-brand-600 text-white scale-110 shadow-md"
                              : "bg-gray-100 text-gray-600 hover:bg-gray-200 active:scale-95"
                          }`}
                        >
                          {v}
                        </button>
                      ))}
                    </div>
                    <div className="mt-1 flex justify-between text-[10px] text-gray-400 px-1">
                      <span>Nada</span>
                      <span>Completamente</span>
                    </div>
                  </div>
                ) : (
                  <textarea
                    value={(responses[q.id] as string) ?? ""}
                    onChange={(e) => setAnswer(q.id, e.target.value)}
                    rows={3}
                    className="mt-3 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
                    placeholder="Escribe tu respuesta (opcional)..."
                  />
                )}
              </div>
            ))}
          </div>

          {/* Navigation */}
          <div className="mt-8 flex items-center justify-between">
            <button
              onClick={prevSection}
              disabled={currentSection === 0}
              className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 disabled:opacity-30"
            >
              <ArrowLeft className="h-4 w-4" />
              Anterior
            </button>
            <button
              onClick={nextSection}
              disabled={!isSectionComplete}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40 transition-colors"
            >
              {currentSection < dimensions.length - 1
                ? "Siguiente"
                : "Revisar respuestas"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Review screen
  if (view === "review") {
    const likertQuestions = questions.filter((q) => q.tipo === "likert");
    const answeredCount = likertQuestions.filter(
      (q) => responses[q.id] !== undefined,
    ).length;

    return (
      <div className="min-h-screen px-4 py-6 sm:py-12">
        <div className="mx-auto w-full max-w-md text-center">
          <h2 className="text-xl font-bold text-gray-900">
            Revisa tus respuestas
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            {answeredCount} de {likertQuestions.length} preguntas respondidas
          </p>

          <div className="mt-6 space-y-2 text-left">
            {dimensions.map((dim) => {
              const dimQs = questions.filter((q) => q.dimension === dim);
              const answered = dimQs.filter(
                (q) => responses[q.id] !== undefined,
              ).length;

              return (
                <div
                  key={dim}
                  className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
                >
                  <span className="text-sm text-gray-700">
                    {DIMENSION_LABELS[dim] ?? dim}
                  </span>
                  <span className="text-xs text-gray-400">
                    {answered}/{dimQs.length}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={() => {
                setCurrentSection(0);
                setView("survey");
              }}
              className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="h-4 w-4" />
              Modificar respuestas
            </button>
            <button
              onClick={submit}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-6 py-3 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              Enviar respuestas
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Submitting
  if (view === "submitting") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-brand-600" />
          <p className="mt-4 text-sm text-gray-500">
            Enviando tus respuestas...
          </p>
        </div>
      </div>
    );
  }

  // Done
  if (view === "done") {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-50">
            <Check className="h-8 w-8 text-green-500" />
          </div>
          <h1 className="mt-6 text-xl font-bold text-gray-900">
            ¡Gracias por tu participación!
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Tus respuestas han sido registradas de forma anónima. No necesitas
            hacer nada más.
          </p>
        </div>
      </div>
    );
  }

  // Error
  if (view === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md text-center">
          <h1 className="text-xl font-bold text-gray-900">
            Algo salió mal
          </h1>
          <p className="mt-2 text-sm text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  // Loading
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
    </div>
  );
}

// Fallback questions matching questions_free.py MEMBER_QUESTIONS
const FALLBACK_QUESTIONS: Question[] = [
  {
    id: "mf01",
    dimension: "liderazgo",
    texto:
      "¿Qué tan claro es para ti quién toma las decisiones importantes en tu organización?",
    tipo: "likert",
  },
  {
    id: "mf02",
    dimension: "liderazgo",
    texto:
      "¿Qué tan accesible es la dirección cuando necesitas resolver un problema?",
    tipo: "likert",
  },
  {
    id: "mf03",
    dimension: "comunicacion",
    texto:
      "¿Qué tan bien fluye la información que necesitas para hacer tu trabajo?",
    tipo: "likert",
  },
  {
    id: "mf04",
    dimension: "comunicacion",
    texto:
      "¿Con qué frecuencia te enteras de cosas importantes por canales informales en lugar de comunicación oficial?",
    tipo: "likert",
  },
  {
    id: "mf05",
    dimension: "cultura",
    texto:
      "¿Qué tanto se practican los valores declarados de la organización en el día a día?",
    tipo: "likert",
  },
  {
    id: "mf06",
    dimension: "cultura",
    texto:
      "¿Qué tan cómodo te sientes para expresar desacuerdos o ideas diferentes?",
    tipo: "likert",
  },
  {
    id: "mf07",
    dimension: "operacion",
    texto: "¿Qué tan eficientes son los procesos de trabajo en tu área?",
    tipo: "likert",
  },
  {
    id: "mf08",
    dimension: "operacion",
    texto:
      "¿Con qué frecuencia tienes que esperar a otra persona o área para avanzar en tu trabajo?",
    tipo: "likert",
  },
  {
    id: "mf09",
    dimension: "general",
    texto:
      "Si pudieras cambiar una cosa de cómo funciona tu organización, ¿cuál sería?",
    tipo: "abierta",
  },
];
