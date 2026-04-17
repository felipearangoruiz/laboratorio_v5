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
import { FREE_LEADER_QUESTIONS, type V2Question, type V2Layer } from "@/lib/types";
import { CheckCircle, ChevronLeft, ChevronRight, Shield } from "lucide-react";

type InterviewMode = "loading" | "free" | "premium";

export default function InterviewPage() {
  const params = useParams();
  const token = params.token as string;

  const [mode, setMode] = useState<InterviewMode>("loading");
  const [memberName, setMemberName] = useState("");
  const [responses, setResponses] = useState<Record<string, any>>({});
  const [questions, setQuestions] = useState<V2Question[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);
  const autoSaveRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Detect interview type
  useEffect(() => {
    async function detect() {
      // Try free endpoint
      try {
        const data = await getFreeInterview(token);
        setMemberName(data.name);
        if (data.responses) setResponses(data.responses);
        if (data.submitted) setSubmitted(true);

        // Use free subset of v2 questions (employee-facing: E1-E4 equivalent)
        // For free members, we use the same G1-G4 base structure
        const freeQuestions: V2Question[] = [
          {
            id: "E1", title: "Tiempo del jefe", dimension: "centralizacion",
            base: { text: "¿Tu jefe dedica su tiempo a decisiones importantes o se la pasa resolviendo cosas del día a día?", type: "single_select", options: ["Se enfoca en lo estratégico", "Hace de todo un poco", "Se la pasa apagando incendios", "No sé en qué se le va el tiempo"] },
            layers: [],
          },
          {
            id: "E2", title: "Ausencia del jefe", dimension: "centralizacion",
            base: { text: "Cuando tu jefe no está o no contesta, ¿qué pasa con el trabajo?", type: "single_select", options: ["Todo sigue normal", "Algunas cosas se retrasan", "Varias cosas quedan paradas", "Casi todo se frena", "Nunca pasa, siempre está disponible"] },
            layers: [],
          },
          {
            id: "E3", title: "Autonomía real", dimension: "centralizacion",
            base: { text: "¿Cuáles de estas cosas puedes decidir SIN pedirle permiso a tu jefe?", type: "multi_select", options: ["Ofrecer descuentos", "Resolver quejas de clientes", "Compras menores", "Cambiar un proceso", "Contratar ayuda temporal", "Negociar con proveedor", "Ninguna"] },
            layers: [],
          },
          {
            id: "E4", title: "Cuellos de botella", dimension: "cuellos_botella",
            base: { text: "¿Dónde se traban las cosas más seguido en tu trabajo?", type: "multi_select", options: ["Aprobaciones que dependen de mi jefe", "Coordinación entre áreas o sedes", "Falta de información", "Falta de herramientas", "Errores y retrabajo", "Proveedores", "Falta de personal", "No se traban"] },
            layers: [],
          },
        ];
        setQuestions(freeQuestions);
        setMode("free");
        setShowWelcome(false);
        setLoading(false);
        return;
      } catch {
        // Not free — try premium
      }

      // Try premium
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

        // Load v2 questions from API
        const instrument = await getPremiumQuestions();
        // Flatten employee sections into question list
        const employeeQs: V2Question[] = (instrument.employee_sections || []).flatMap(
          (s: any) => s.questions
        );
        setQuestions(employeeQs);
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

  // Auto-save (premium only)
  const doAutoSave = useCallback(async () => {
    if (mode !== "premium" || Object.keys(responses).length === 0) return;
    try { await saveDraft(token, responses); } catch { /* silent */ }
  }, [token, responses, mode]);

  useEffect(() => {
    if (showWelcome || submitted || mode === "free") return;
    autoSaveRef.current = setInterval(doAutoSave, 30_000);
    return () => { if (autoSaveRef.current) clearInterval(autoSaveRef.current); };
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
        await submitFreeInterview(token, responses);
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

  // Check if a layer's condition is met
  function isLayerActive(q: V2Question, layer: V2Layer): boolean {
    const cond = layer.condition;
    if (cond.always) return true;

    const baseAnswer = responses[q.id];

    if (cond.base_answer_index_gte !== undefined) {
      if (typeof baseAnswer !== "number" || baseAnswer < cond.base_answer_index_gte) return false;
    }
    if (cond.base_answer_index_not !== undefined) {
      if (baseAnswer === cond.base_answer_index_not) return false;
    }
    if (cond.base_answer_index !== undefined) {
      if (baseAnswer !== cond.base_answer_index) return false;
    }
    if (cond.base_has_selections) {
      if (!Array.isArray(baseAnswer) || baseAnswer.length === 0) return false;
    }
    if (cond.base_excludes) {
      if (Array.isArray(baseAnswer) && cond.base_excludes.some((ex: string) => baseAnswer.includes(ex))) return false;
    }
    if (cond.base_excludes_all) {
      if (Array.isArray(baseAnswer) && cond.base_excludes_all.every((ex: string) => !baseAnswer.includes(ex))) return true;
      if (Array.isArray(baseAnswer)) return false;
      return true;
    }
    if (cond.base_selection_count_gte) {
      if (!Array.isArray(baseAnswer) || baseAnswer.length < cond.base_selection_count_gte) return false;
    }

    return true;
  }

  // Render a single question (base + active layers)
  function renderQuestion(q: V2Question) {
    return (
      <div key={q.id} className="space-y-5">
        {/* Title */}
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
          {q.title}
        </h3>

        {/* Base question */}
        {renderBaseQuestion(q)}

        {/* Conditional layers */}
        {q.layers.map((layer) => {
          if (!isLayerActive(q, layer)) return null;
          return renderLayer(q, layer);
        })}
      </div>
    );
  }

  function renderBaseQuestion(q: V2Question) {
    const { base } = q;

    if (base.type === "single_select") {
      return (
        <div className="space-y-2">
          <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
          <div className="space-y-1.5">
            {base.options.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => setResponse(q.id, idx)}
                className={`w-full text-left px-4 py-2.5 text-sm rounded-lg border transition-colors ${
                  responses[q.id] === idx
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-700 border-gray-200 hover:border-gray-400"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (base.type === "multi_select") {
      const selected: string[] = responses[q.id] || [];
      return (
        <div className="space-y-2">
          <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
          <p className="text-xs text-gray-400">Selecciona todas las que apliquen</p>
          <div className="flex flex-wrap gap-2">
            {base.options.map((opt) => (
              <button
                key={opt}
                onClick={() => toggleMultiSelect(q.id, opt)}
                className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                  selected.includes(opt)
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (base.type === "text_open" || base.type === "text_short") {
      return (
        <div className="space-y-2">
          <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
          <textarea
            value={responses[q.id] || ""}
            onChange={(e) => setResponse(q.id, e.target.value)}
            rows={base.type === "text_open" ? 4 : 2}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none resize-none"
            placeholder="Escribe tu respuesta..."
          />
        </div>
      );
    }

    if (base.type === "scale_1_5") {
      return (
        <div className="space-y-2">
          <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
          <div className="flex gap-1.5">
            {base.options.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => setResponse(q.id, idx)}
                className={`flex-1 py-2.5 text-xs rounded-lg border transition-colors ${
                  responses[q.id] === idx
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (base.type === "numeric_input") {
      return (
        <div className="space-y-2">
          <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
          <input
            type="number"
            value={responses[q.id] ?? ""}
            onChange={(e) => setResponse(q.id, e.target.value ? Number(e.target.value) : undefined)}
            className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
            min={0}
          />
        </div>
      );
    }

    return null;
  }

  function renderLayer(q: V2Question, layer: V2Layer) {
    const layerId = layer.id;

    if (layer.type === "numeric_select" || layer.type === "single_select") {
      const options = layer.options || [];
      return (
        <div key={layerId} className="pl-4 border-l-2 border-gray-200 space-y-2">
          <p className="text-sm text-gray-600">{layer.text}</p>
          <div className="space-y-1.5">
            {options.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => setResponse(layerId, idx)}
                className={`w-full text-left px-4 py-2 text-sm rounded-lg border transition-colors ${
                  responses[layerId] === idx
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-700 border-gray-200 hover:border-gray-400"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (layer.type === "text_short") {
      return (
        <div key={layerId} className="pl-4 border-l-2 border-gray-200 space-y-2">
          <p className="text-sm text-gray-600">{layer.text}</p>
          <textarea
            value={responses[layerId] || ""}
            onChange={(e) => setResponse(layerId, e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none resize-none"
            placeholder="Escribe tu respuesta..."
          />
        </div>
      );
    }

    if (layer.type === "numeric_input") {
      return (
        <div key={layerId} className="pl-4 border-l-2 border-gray-200 space-y-2">
          <p className="text-sm text-gray-600">{layer.text}</p>
          <input
            type="number"
            value={responses[layerId] ?? ""}
            onChange={(e) => setResponse(layerId, e.target.value ? Number(e.target.value) : undefined)}
            className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
            min={0}
          />
        </div>
      );
    }

    if (layer.type === "gradient_per_selection") {
      const baseAnswer: string[] = responses[q.id] || [];
      const excludes = layer.condition?.base_excludes || [];
      const items = baseAnswer.filter((a) => !excludes.includes(a));
      if (items.length === 0) return null;

      const gradientData: Record<string, { frequency?: number; severity?: number }> =
        responses[layerId] || {};

      return (
        <div key={layerId} className="pl-4 border-l-2 border-gray-200 space-y-4">
          <p className="text-sm text-gray-600 font-medium">{layer.text}</p>
          {items.map((item) => (
            <div key={item} className="space-y-2 bg-gray-50 rounded-lg p-3">
              <p className="text-sm font-medium text-gray-700">{item}</p>
              {layer.frequency_options && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Frecuencia:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {layer.frequency_options.map((opt, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const updated = { ...gradientData, [item]: { ...gradientData[item], frequency: idx } };
                          setResponse(layerId, updated);
                        }}
                        className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                          gradientData[item]?.frequency === idx
                            ? "bg-gray-900 text-white border-gray-900"
                            : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {layer.severity_options && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Severidad:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {layer.severity_options.map((opt, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const updated = { ...gradientData, [item]: { ...gradientData[item], severity: idx } };
                          setResponse(layerId, updated);
                        }}
                        className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                          gradientData[item]?.severity === idx
                            ? "bg-gray-900 text-white border-gray-900"
                            : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      );
    }

    if (layer.type === "ranking_from_selected" || layer.type === "ranking_from_unselected") {
      const baseAnswer: string[] = responses[q.id] || [];
      const allOptions = q.base.options;
      const pool =
        layer.type === "ranking_from_selected"
          ? baseAnswer
          : allOptions.filter((o) => !baseAnswer.includes(o));

      if (pool.length === 0) return null;

      const ranking: string[] = responses[layerId] || [];
      const maxItems = layer.max_items || 1;

      return (
        <div key={layerId} className="pl-4 border-l-2 border-gray-200 space-y-2">
          <p className="text-sm text-gray-600">{layer.text}</p>
          <div className="space-y-1.5">
            {pool.map((opt) => {
              const idx = ranking.indexOf(opt);
              const isSelected = idx >= 0;
              return (
                <button
                  key={opt}
                  onClick={() => {
                    let updated: string[];
                    if (isSelected) {
                      updated = ranking.filter((r) => r !== opt);
                    } else if (ranking.length < maxItems) {
                      updated = [...ranking, opt];
                    } else {
                      return;
                    }
                    setResponse(layerId, updated);
                  }}
                  className={`w-full text-left px-4 py-2 text-sm rounded-lg border transition-colors ${
                    isSelected
                      ? "bg-gray-900 text-white border-gray-900"
                      : "bg-white text-gray-700 border-gray-200 hover:border-gray-400"
                  }`}
                >
                  {isSelected ? `${idx + 1}. ` : ""}{opt}
                </button>
              );
            })}
          </div>
        </div>
      );
    }

    return null;
  }

  // Progress
  const totalQ = questions.length;
  const answeredQ = questions.filter((q) => responses[q.id] !== undefined).length;
  const progressPct = totalQ > 0 ? Math.round((answeredQ / totalQ) * 100) : 0;
  const currentQ = questions[currentIdx];
  const isLast = currentIdx === questions.length - 1;

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
            Duración estimada: 10-15 minutos. Puedes guardar tu progreso y volver después.
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

  // Question-by-question flow (both free and premium)
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Progress bar */}
      <div className="sticky top-0 bg-white border-b border-gray-100 z-10">
        <div className="h-1 bg-gray-100">
          <div
            className="h-1 bg-gray-900 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <div className="flex items-center justify-between px-4 py-2">
          <span className="text-xs text-gray-500">
            Pregunta {currentIdx + 1} de {totalQ}
          </span>
          <span className="text-xs font-medium text-gray-700">{currentQ?.title}</span>
          <span className="text-xs text-gray-500">{progressPct}%</span>
        </div>
      </div>

      {/* Question */}
      <div className="flex-1 max-w-lg mx-auto w-full px-4 py-6">
        {error && (
          <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-lg">{error}</div>
        )}
        {currentQ && renderQuestion(currentQ)}
      </div>

      {/* Navigation */}
      <div className="sticky bottom-0 bg-white border-t border-gray-100 px-4 py-3">
        <div className="max-w-lg mx-auto flex gap-3">
          {currentIdx > 0 && (
            <button
              onClick={() => setCurrentIdx((i) => i - 1)}
              className="inline-flex items-center gap-1 px-4 py-2.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <ChevronLeft className="w-4 h-4" />
              Anterior
            </button>
          )}
          {isLast ? (
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
                if (mode === "premium") doAutoSave();
                setCurrentIdx((i) => i + 1);
              }}
              disabled={responses[currentQ?.id] === undefined}
              className="flex-1 inline-flex items-center justify-center gap-1 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              Siguiente
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
        {mode === "premium" && (
          <p className="mt-2 text-center text-[10px] text-gray-400">
            Progreso guardado automáticamente
          </p>
        )}
      </div>
    </div>
  );
}
