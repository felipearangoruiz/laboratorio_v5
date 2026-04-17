"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import {
  getFreeInterview,
  submitFreeInterview,
  getPublicInterview,
  submitInterview,
  saveDraft,
  getPremiumQuestions,
  ApiError,
} from "@/lib/api";
import { FREE_DIMENSIONS } from "@/lib/types";
import { CheckCircle, ChevronLeft, ChevronRight, Shield } from "lucide-react";

type InterviewMode = "loading" | "free" | "premium";

interface Section {
  dimension: string;
  label: string;
  questions: {
    id: string;
    dimension: string;
    tipo: string;
    texto: string;
    opciones?: string[];
  }[];
}

const LIKERT_OPTIONS = [
  { value: 1, label: "Muy en desacuerdo" },
  { value: 2, label: "En desacuerdo" },
  { value: 3, label: "Neutral" },
  { value: 4, label: "De acuerdo" },
  { value: 5, label: "Muy de acuerdo" },
];

export default function InterviewPage() {
  const params = useParams();
  const token = params.token as string;

  const [mode, setMode] = useState<InterviewMode>("loading");
  const [memberName, setMemberName] = useState("");
  const [responses, setResponses] = useState<Record<string, any>>({});
  const [sections, setSections] = useState<Section[]>([]);
  const [currentSection, setCurrentSection] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);
  const autoSaveRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Detect interview type: try free first, then premium
  useEffect(() => {
    async function detect() {
      // Try free (quick assessment) endpoint
      try {
        const data = await getFreeInterview(token);
        setMemberName(data.name);
        if (data.responses) setResponses(data.responses);
        if (data.submitted) setSubmitted(true);

        // Build sections from FREE_DIMENSIONS
        const freeSections: Section[] = FREE_DIMENSIONS.map((d) => ({
          dimension: d.id,
          label: d.label,
          questions: d.questions.map((q) => ({
            id: q.id,
            dimension: q.dimension,
            tipo: "likert",
            texto: q.text,
          })),
        }));
        setSections(freeSections);
        setMode("free");
        setLoading(false);
        return;
      } catch (err) {
        // Not a free token — try premium
      }

      // Try premium (/entrevista/) endpoint
      try {
        const data = await getPublicInterview(token);
        setMemberName(data.name);
        if (data.data && Object.keys(data.data).length > 0) {
          setResponses(data.data);
          setShowWelcome(false);
        }
        if (data.token_status === "COMPLETED" || data.token_status === "completed") {
          setSubmitted(true);
        }

        // Load premium questions
        const premiumSections = await getPremiumQuestions();
        setSections(premiumSections);
        setMode("premium");
        setLoading(false);
      } catch (err) {
        if (err instanceof ApiError) setError(err.message);
        else setError("Enlace de entrevista no válido.");
        setLoading(false);
      }
    }
    detect();
  }, [token]);

  // Auto-save every 30 seconds (premium only)
  const doAutoSave = useCallback(async () => {
    if (mode !== "premium" || Object.keys(responses).length === 0) return;
    try {
      await saveDraft(token, responses);
    } catch {
      // silent
    }
  }, [token, responses, mode]);

  useEffect(() => {
    if (showWelcome || submitted || mode === "free") return;
    autoSaveRef.current = setInterval(doAutoSave, 30_000);
    return () => {
      if (autoSaveRef.current) clearInterval(autoSaveRef.current);
    };
  }, [doAutoSave, showWelcome, submitted, mode]);

  function setResponse(questionId: string, value: any) {
    setResponses((prev) => ({ ...prev, [questionId]: value }));
  }

  function toggleMultiSelect(questionId: string, option: string) {
    setResponses((prev) => {
      const current: string[] = prev[questionId] || [];
      const updated = current.includes(option)
        ? current.filter((o: string) => o !== option)
        : [...current, option];
      return { ...prev, [questionId]: updated };
    });
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError("");
    try {
      if (mode === "free") {
        // Filter to only numeric responses for free
        const numericResponses: Record<string, number> = {};
        for (const [k, v] of Object.entries(responses)) {
          if (typeof v === "number") numericResponses[k] = v;
        }
        await submitFreeInterview(token, numericResponses);
      } else {
        await submitInterview(token, responses);
      }
      setSubmitted(true);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Error al enviar respuestas.");
    } finally {
      setSubmitting(false);
    }
  }

  const section = sections[currentSection];
  const isLastSection = currentSection === sections.length - 1;
  const totalQuestions = sections.reduce((sum, s) => sum + s.questions.length, 0);
  const answeredQuestions = Object.keys(responses).filter(
    (k) => !k.startsWith("_")
  ).length;
  const progressPct =
    totalQuestions > 0 ? Math.round((answeredQuestions / totalQuestions) * 100) : 0;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    );
  }

  if (error && !memberName) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="text-center max-w-sm">
          <h1 className="text-lg font-semibold text-gray-900">Enlace no válido</h1>
          <p className="mt-2 text-sm text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="text-center max-w-sm">
          <CheckCircle className="w-14 h-14 text-emerald-500 mx-auto" />
          <h1 className="mt-4 text-xl font-bold text-gray-900">
            ¡Gracias, {memberName}!
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Tu respuesta ha sido registrada. Puedes cerrar esta página.
          </p>
        </div>
      </div>
    );
  }

  if (showWelcome && mode === "premium") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="text-center max-w-sm">
          <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-gray-900">Hola, {memberName}</h1>
          <p className="mt-3 text-sm text-gray-600 leading-relaxed">
            Has sido invitado(a) a participar en un diagnóstico organizacional.
            Tu identidad es anónima y tus respuestas serán confidenciales.
          </p>
          <div className="mt-4 p-3 bg-blue-50 rounded-lg text-xs text-blue-700">
            Duración estimada: 15-25 minutos. Puedes guardar tu progreso y volver después.
          </div>
          <button
            onClick={() => setShowWelcome(false)}
            className="mt-6 w-full py-3 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800"
          >
            Comenzar encuesta
          </button>
        </div>
      </div>
    );
  }

  // For free mode, skip welcome and show all questions at once
  if (mode === "free") {
    const allQuestions = sections.flatMap((s) => s.questions);
    const allAnswered = allQuestions.every((q) => responses[q.id] !== undefined);

    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-lg mx-auto px-4 py-8">
          <div className="text-center mb-8">
            <h1 className="text-xl font-bold text-gray-900">Encuesta organizacional</h1>
            <p className="mt-1 text-sm text-gray-500">
              Hola {memberName}. Esta encuesta es anónima y toma menos de 5 minutos.
            </p>
          </div>
          {error && (
            <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-lg">{error}</div>
          )}
          <div className="space-y-8">
            {sections.map((dim) => (
              <div key={dim.dimension}>
                <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                  {dim.label}
                </h2>
                <div className="mt-3 space-y-5">
                  {dim.questions.map((q) => (
                    <div key={q.id}>
                      <p className="text-sm text-gray-700">{q.texto}</p>
                      <div className="mt-2 flex gap-1">
                        {LIKERT_OPTIONS.map((opt) => (
                          <button
                            key={opt.value}
                            onClick={() => setResponse(q.id, opt.value)}
                            className={`flex-1 py-2.5 text-xs rounded-md border transition-colors ${
                              responses[q.id] === opt.value
                                ? "bg-gray-900 text-white border-gray-900"
                                : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                            }`}
                            title={opt.label}
                          >
                            {opt.value}
                          </button>
                        ))}
                      </div>
                      <div className="flex justify-between mt-1">
                        <span className="text-[10px] text-gray-400">Muy en desacuerdo</span>
                        <span className="text-[10px] text-gray-400">Muy de acuerdo</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-8">
            <button
              onClick={handleSubmit}
              disabled={!allAnswered || submitting}
              className="w-full py-3 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              {submitting ? "Enviando..." : "Enviar respuestas"}
            </button>
            {!allAnswered && (
              <p className="mt-2 text-xs text-gray-400 text-center">
                Responde todas las preguntas ({answeredQuestions}/{allQuestions.length})
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Premium: section-by-section
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="sticky top-0 bg-white border-b border-gray-100 z-10">
        <div className="h-1 bg-gray-100">
          <div
            className="h-1 bg-gray-900 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <div className="flex items-center justify-between px-4 py-2">
          <span className="text-xs text-gray-500">
            Sección {currentSection + 1} de {sections.length}
          </span>
          <span className="text-xs font-medium text-gray-700">{section?.label}</span>
          <span className="text-xs text-gray-500">{progressPct}%</span>
        </div>
      </div>

      <div className="flex-1 max-w-lg mx-auto w-full px-4 py-6">
        {error && (
          <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-lg">{error}</div>
        )}
        {section && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-gray-900">{section.label}</h2>
            {section.questions.map((q) => (
              <div key={q.id} className="space-y-2">
                <p className="text-sm text-gray-700 leading-relaxed">{q.texto}</p>
                {q.tipo === "likert" && (
                  <div className="flex gap-1.5">
                    {LIKERT_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setResponse(q.id, opt.value)}
                        className={`flex-1 py-2.5 text-xs rounded-lg border transition-colors ${
                          responses[q.id] === opt.value
                            ? "bg-gray-900 text-white border-gray-900"
                            : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                        }`}
                        title={opt.label}
                      >
                        {opt.value}
                      </button>
                    ))}
                  </div>
                )}
                {q.tipo === "abierta" && (
                  <textarea
                    value={responses[q.id] || ""}
                    onChange={(e) => setResponse(q.id, e.target.value)}
                    rows={3}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none resize-none"
                    placeholder="Escribe tu respuesta..."
                  />
                )}
                {q.tipo === "seleccion_multiple" && q.opciones && (
                  <div className="flex flex-wrap gap-2">
                    {q.opciones.map((opt) => {
                      const selected = (responses[q.id] || []).includes(opt);
                      return (
                        <button
                          key={opt}
                          onClick={() => toggleMultiSelect(q.id, opt)}
                          className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
                            selected
                              ? "bg-gray-900 text-white border-gray-900"
                              : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                          }`}
                        >
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="sticky bottom-0 bg-white border-t border-gray-100 px-4 py-3">
        <div className="max-w-lg mx-auto flex gap-3">
          {currentSection > 0 && (
            <button
              onClick={() => setCurrentSection((s) => s - 1)}
              className="inline-flex items-center gap-1 px-4 py-2.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <ChevronLeft className="w-4 h-4" />
              Anterior
            </button>
          )}
          {isLastSection ? (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex-1 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              {submitting ? "Enviando..." : "Enviar respuestas"}
            </button>
          ) : (
            <button
              onClick={() => {
                doAutoSave();
                setCurrentSection((s) => s + 1);
              }}
              className="flex-1 inline-flex items-center justify-center gap-1 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800"
            >
              Siguiente
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
        <p className="mt-2 text-center text-[10px] text-gray-400">
          Progreso guardado automáticamente
        </p>
      </div>
    </div>
  );
}
