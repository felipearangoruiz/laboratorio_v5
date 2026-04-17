"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import {
  getPublicInterview,
  submitInterview,
  saveDraft,
  getPremiumQuestions,
  ApiError,
} from "@/lib/api";
import { CheckCircle, ChevronLeft, ChevronRight, Shield } from "lucide-react";

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

  // Load interview state and questions
  useEffect(() => {
    async function load() {
      try {
        const [interview, questionSections] = await Promise.all([
          getPublicInterview(token),
          getPremiumQuestions(),
        ]);
        setMemberName(interview.name);
        setSections(questionSections);
        if (interview.data && Object.keys(interview.data).length > 0) {
          setResponses(interview.data);
          setShowWelcome(false);
        }
        if (interview.token_status === "COMPLETED" || interview.token_status === "completed") {
          setSubmitted(true);
        }
      } catch (err) {
        if (err instanceof ApiError) setError(err.message);
        else setError("Error al cargar la entrevista.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  // Auto-save every 30 seconds
  const doAutoSave = useCallback(async () => {
    if (Object.keys(responses).length === 0) return;
    try {
      await saveDraft(token, responses);
    } catch {
      // Silent fail
    }
  }, [token, responses]);

  useEffect(() => {
    if (showWelcome || submitted) return;
    autoSaveRef.current = setInterval(doAutoSave, 30_000);
    return () => {
      if (autoSaveRef.current) clearInterval(autoSaveRef.current);
    };
  }, [doAutoSave, showWelcome, submitted]);

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
      await submitInterview(token, responses);
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
  const progressPct = totalQuestions > 0 ? Math.round((answeredQuestions / totalQuestions) * 100) : 0;

  // Check if current section is complete
  const sectionComplete = section
    ? section.questions.every((q) => {
        const val = responses[q.id];
        if (q.tipo === "likert") return typeof val === "number";
        if (q.tipo === "abierta") return typeof val === "string" && val.trim().length > 0;
        if (q.tipo === "seleccion_multiple") return Array.isArray(val) && val.length > 0;
        return false;
      })
    : false;

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
            Tu respuesta ha sido registrada. Tus comentarios contribuirán al
            diagnóstico organizacional. Puedes cerrar esta página.
          </p>
        </div>
      </div>
    );
  }

  if (showWelcome) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="text-center max-w-sm">
          <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-gray-900">
            Hola, {memberName}
          </h1>
          <p className="mt-3 text-sm text-gray-600 leading-relaxed">
            Has sido invitado(a) a participar en un diagnóstico organizacional.
            Tu identidad es anónima y tus respuestas serán tratadas de forma
            confidencial.
          </p>
          <div className="mt-4 p-3 bg-blue-50 rounded-lg text-xs text-blue-700">
            Duración estimada: 15-25 minutos. Puedes guardar tu progreso y
            volver después.
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

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Progress header */}
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
          <span className="text-xs font-medium text-gray-700">
            {section?.label}
          </span>
          <span className="text-xs text-gray-500">{progressPct}%</span>
        </div>
      </div>

      {/* Section content */}
      <div className="flex-1 max-w-lg mx-auto w-full px-4 py-6">
        {error && (
          <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-lg">
            {error}
          </div>
        )}

        {section && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-gray-900">{section.label}</h2>

            {section.questions.map((q) => (
              <div key={q.id} className="space-y-2">
                <p className="text-sm text-gray-700 leading-relaxed">
                  {q.texto}
                </p>

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
                      const selected = (
                        responses[q.id] || []
                      ).includes(opt);
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

      {/* Navigation */}
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
