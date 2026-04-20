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

// Shared option class builders
const optionCls = (selected: boolean) =>
  `w-full text-left px-4 py-2.5 text-sm rounded-md border transition-colors ${
    selected
      ? "border-accent bg-accent-light text-warm-900 font-medium"
      : "border-warm-200 bg-white text-warm-700 hover:border-warm-300"
  }`;

const chipCls = (selected: boolean) =>
  `px-3 py-1.5 text-sm rounded-full border transition-colors ${
    selected
      ? "border-accent bg-accent-light text-warm-900 font-medium"
      : "border-warm-200 bg-white text-warm-600 hover:border-warm-300"
  }`;

const scaleCls = (selected: boolean) =>
  `flex-1 py-2.5 text-xs rounded-md border transition-colors ${
    selected
      ? "border-accent bg-accent-light text-warm-900 font-medium"
      : "border-warm-200 bg-white text-warm-600 hover:border-warm-300"
  }`;

const microCls = (selected: boolean) =>
  `px-2.5 py-1 text-xs rounded-md border transition-colors ${
    selected
      ? "border-accent bg-accent-light text-warm-900 font-medium"
      : "border-warm-200 bg-white text-warm-600 hover:border-warm-300"
  }`;

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

  // ── Detect interview type ────────────────────────────────
  useEffect(() => {
    async function detect() {
      try {
        const data = await getFreeInterview(token);
        setMemberName(data.name);
        if (data.responses) setResponses(data.responses);
        if (data.submitted) setSubmitted(true);
        if (Array.isArray(data.questions) && data.questions.length > 0) {
          setQuestions(data.questions);
        }
        setMode("free");
        setShowWelcome(false);
        setLoading(false);
        return;
      } catch {
        // Not free — try premium
      }

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
        const instrument = await getPremiumQuestions();
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

  // ── Auto-save (premium only) ─────────────────────────────
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

  // ── Layer condition logic ────────────────────────────────
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

  // ── Render question ──────────────────────────────────────
  function renderQuestion(q: V2Question) {
    return (
      <div key={q.id} className="space-y-6">
        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-accent">{q.title}</p>
        {renderBaseQuestion(q)}
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
          <p className="text-base text-warm-900 leading-relaxed font-medium">{base.text}</p>
          <div className="space-y-2 mt-3">
            {base.options.map((opt, idx) => (
              <button key={idx} onClick={() => setResponse(q.id, idx)} className={optionCls(responses[q.id] === idx)}>
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
          <p className="text-base text-warm-900 leading-relaxed font-medium">{base.text}</p>
          <p className="text-xs text-warm-400">Selecciona todas las que apliquen</p>
          <div className="flex flex-wrap gap-2 mt-2">
            {base.options.map((opt) => (
              <button key={opt} onClick={() => toggleMultiSelect(q.id, opt)} className={chipCls(selected.includes(opt))}>
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
          <p className="text-base text-warm-900 leading-relaxed font-medium">{base.text}</p>
          <textarea
            value={responses[q.id] || ""}
            onChange={(e) => setResponse(q.id, e.target.value)}
            rows={base.type === "text_open" ? 4 : 2}
            className="w-full rounded-md border border-warm-300 bg-white px-3 py-2.5 text-sm text-warm-900 focus:border-accent focus:ring-1 focus:ring-accent outline-none resize-none placeholder:text-warm-400"
            placeholder="Escribe tu respuesta..."
          />
        </div>
      );
    }

    if (base.type === "scale_1_5") {
      return (
        <div className="space-y-2">
          <p className="text-base text-warm-900 leading-relaxed font-medium">{base.text}</p>
          <div className="flex gap-1.5 mt-3">
            {base.options.map((opt, idx) => (
              <button key={idx} onClick={() => setResponse(q.id, idx)} className={scaleCls(responses[q.id] === idx)}>
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
          <p className="text-base text-warm-900 leading-relaxed font-medium">{base.text}</p>
          <input
            type="number"
            value={responses[q.id] ?? ""}
            onChange={(e) => setResponse(q.id, e.target.value ? Number(e.target.value) : undefined)}
            className="w-32 rounded-md border border-warm-300 bg-white px-3 py-2.5 text-sm text-warm-900 focus:border-accent focus:ring-1 focus:ring-accent outline-none"
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
        <div key={layerId} className="pl-4 border-l-2 border-warm-200 space-y-2">
          <p className="text-sm text-warm-600">{layer.text}</p>
          <div className="space-y-1.5">
            {options.map((opt, idx) => (
              <button key={idx} onClick={() => setResponse(layerId, idx)} className={optionCls(responses[layerId] === idx)}>
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (layer.type === "text_short") {
      return (
        <div key={layerId} className="pl-4 border-l-2 border-warm-200 space-y-2">
          <p className="text-sm text-warm-600">{layer.text}</p>
          <textarea
            value={responses[layerId] || ""}
            onChange={(e) => setResponse(layerId, e.target.value)}
            rows={2}
            className="w-full rounded-md border border-warm-300 bg-white px-3 py-2 text-sm text-warm-900 focus:border-accent focus:ring-1 focus:ring-accent outline-none resize-none placeholder:text-warm-400"
            placeholder="Escribe tu respuesta..."
          />
        </div>
      );
    }

    if (layer.type === "numeric_input") {
      return (
        <div key={layerId} className="pl-4 border-l-2 border-warm-200 space-y-2">
          <p className="text-sm text-warm-600">{layer.text}</p>
          <input
            type="number"
            value={responses[layerId] ?? ""}
            onChange={(e) => setResponse(layerId, e.target.value ? Number(e.target.value) : undefined)}
            className="w-32 rounded-md border border-warm-300 bg-white px-3 py-2 text-sm text-warm-900 focus:border-accent focus:ring-1 focus:ring-accent outline-none"
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
        <div key={layerId} className="pl-4 border-l-2 border-warm-200 space-y-4">
          <p className="text-sm font-medium text-warm-700">{layer.text}</p>
          {items.map((item) => (
            <div key={item} className="space-y-2 bg-warm-50 rounded-lg p-3 border border-warm-200">
              <p className="text-sm font-medium text-warm-900">{item}</p>
              {layer.frequency_options && (
                <div>
                  <p className="text-xs text-warm-400 mb-1.5">Frecuencia:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {layer.frequency_options.map((opt, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const updated = { ...gradientData, [item]: { ...gradientData[item], frequency: idx } };
                          setResponse(layerId, updated);
                        }}
                        className={microCls(gradientData[item]?.frequency === idx)}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {layer.severity_options && (
                <div>
                  <p className="text-xs text-warm-400 mb-1.5">Severidad:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {layer.severity_options.map((opt, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const updated = { ...gradientData, [item]: { ...gradientData[item], severity: idx } };
                          setResponse(layerId, updated);
                        }}
                        className={microCls(gradientData[item]?.severity === idx)}
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
        <div key={layerId} className="pl-4 border-l-2 border-warm-200 space-y-2">
          <p className="text-sm text-warm-600">{layer.text}</p>
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
                  className={optionCls(isSelected)}
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

  // ── Derived state ────────────────────────────────────────
  const totalQ = questions.length;
  const answeredQ = questions.filter((q) => responses[q.id] !== undefined).length;
  const progressPct = totalQ > 0 ? Math.round((answeredQ / totalQ) * 100) : 0;
  const currentQ = questions[currentIdx];
  const isLast = currentIdx === questions.length - 1;

  // ── Loading ──────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-warm-50">
        <div className="w-8 h-8 border-2 border-warm-200 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────
  if (error && !memberName) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-warm-50 px-4">
        <div className="text-center max-w-sm">
          <h1 className="font-display italic text-xl text-warm-900">Enlace no válido</h1>
          <p className="mt-2 text-sm text-warm-500">{error}</p>
        </div>
      </div>
    );
  }

  // ── Submitted ────────────────────────────────────────────
  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-warm-50 px-4">
        <div className="text-center max-w-sm">
          <CheckCircle className="w-14 h-14 text-success mx-auto" />
          <h1 className="mt-4 font-display italic text-2xl text-warm-900">
            ¡Gracias, {memberName}!
          </h1>
          <p className="mt-2 text-sm text-warm-500 leading-relaxed">
            Tu respuesta ha sido registrada de forma anónima. Puedes cerrar esta página.
          </p>
        </div>
      </div>
    );
  }

  // ── Welcome (premium) ─────────────────────────────────────
  if (showWelcome && mode === "premium") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-warm-50 px-4">
        <div className="text-center max-w-sm">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-warm-100">
            <Shield className="w-6 h-6 text-warm-500" strokeWidth={1.5} />
          </div>
          <h1 className="font-display italic text-2xl text-warm-900">
            Hola, {memberName}
          </h1>
          <p className="mt-3 text-sm text-warm-600 leading-relaxed">
            Has sido invitado(a) a participar en un diagnóstico organizacional.
            Tu identidad es anónima y tus respuestas serán confidenciales.
          </p>
          <div className="mt-4 p-3 bg-accent/8 rounded-md border border-accent/20 text-xs text-accent font-medium">
            Duración estimada: 10–15 minutos. Puedes guardar tu progreso y volver después.
          </div>
          <button
            onClick={() => setShowWelcome(false)}
            className="mt-6 w-full py-3 bg-accent text-white text-sm font-semibold rounded-md hover:bg-accent-hover transition-colors"
          >
            Comenzar encuesta
          </button>
        </div>
      </div>
    );
  }

  // ── Main interview flow ───────────────────────────────────
  return (
    <div className="min-h-screen bg-warm-50 flex flex-col">
      {/* Progress bar — thin accent line at top */}
      <div className="sticky top-0 z-10 bg-white border-b border-warm-200 shadow-warm-sm">
        <div className="h-[2px] bg-warm-100">
          <div
            className="h-full bg-accent transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <div className="flex items-center justify-between px-4 py-2.5">
          <span className="text-xs text-warm-400">
            Pregunta {currentIdx + 1} de {totalQ}
          </span>
          <span className="text-xs font-semibold text-warm-600 truncate max-w-[40%] text-center">
            {currentQ?.title}
          </span>
          <span className="text-xs text-warm-400">{progressPct}%</span>
        </div>
      </div>

      {/* Question content */}
      <div className="flex-1 max-w-lg mx-auto w-full px-4 py-8">
        {error && (
          <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-md border border-red-200">
            {error}
          </div>
        )}
        {currentQ && renderQuestion(currentQ)}
      </div>

      {/* Navigation */}
      <div className="sticky bottom-0 bg-white border-t border-warm-200 px-4 py-4 shadow-warm-sm">
        <div className="max-w-lg mx-auto flex gap-3">
          {currentIdx > 0 && (
            <button
              onClick={() => setCurrentIdx((i) => i - 1)}
              className="inline-flex items-center gap-1 px-4 py-2.5 text-sm font-medium text-warm-700 border border-warm-200 rounded-md hover:bg-warm-50 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Anterior
            </button>
          )}
          {isLast ? (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex-1 py-2.5 bg-accent text-white text-sm font-semibold rounded-md hover:bg-accent-hover disabled:opacity-50 transition-colors"
            >
              {submitting ? "Enviando…" : "Enviar respuestas"}
            </button>
          ) : (
            <button
              onClick={() => {
                if (mode === "premium") doAutoSave();
                setCurrentIdx((i) => i + 1);
              }}
              disabled={responses[currentQ?.id] === undefined}
              className="flex-1 inline-flex items-center justify-center gap-1 py-2.5 bg-accent text-white text-sm font-semibold rounded-md hover:bg-accent-hover disabled:opacity-50 transition-colors"
            >
              Siguiente
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
        {mode === "premium" && (
          <p className="mt-2 text-center text-[10px] text-warm-400">
            Progreso guardado automáticamente
          </p>
        )}
      </div>
    </div>
  );
}
