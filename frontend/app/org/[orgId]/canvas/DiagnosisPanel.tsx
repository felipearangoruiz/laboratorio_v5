"use client";

import { useState } from "react";
import {
  X,
  FileDown,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Lightbulb,
  AlertCircle,
  CheckCircle2,
  Minus,
} from "lucide-react";
import type { DiagnosisResult } from "@/lib/api";

interface Props {
  diagnosis: DiagnosisResult;
  onClose: () => void;
}

// ── Score bar ──────────────────────────────────────────────────────
function ScoreBar({ label, score, avg }: { label: string; score: number; avg?: number }) {
  const pct = Math.round(Math.min(100, Math.max(0, score * 20))); // 0-5 → 0-100%
  const color =
    score >= 3.8 ? "bg-emerald-500" : score >= 2.5 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-warm-700 w-36 truncate capitalize">{label}</span>
      <div className="flex-1 h-2 bg-warm-100 rounded-full overflow-hidden relative">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
        {avg !== undefined && (
          <div
            className="absolute top-0 bottom-0 w-px bg-warm-400/60"
            style={{ left: `${Math.round(avg * 20)}%` }}
            title={`Promedio org: ${avg.toFixed(1)}`}
          />
        )}
      </div>
      <span className="text-sm font-semibold text-warm-900 w-8 text-right tabular-nums">
        {score.toFixed(1)}
      </span>
    </div>
  );
}

// ── Confidence badge ──────────────────────────────────────────────
function normalizeConfidence(c: string | number): "high" | "medium" | "low" {
  if (typeof c === "number") {
    if (c >= 0.7) return "high";
    if (c >= 0.45) return "medium";
    return "low";
  }
  const lower = c.toLowerCase();
  if (lower === "high" || lower === "alta") return "high";
  if (lower === "low" || lower === "baja") return "low";
  return "medium";
}

function ConfidenceBadge({ confidence }: { confidence: string | number }) {
  const map: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    high:   { label: "Alta", cls: "bg-green-50 text-green-700 border-green-200", icon: <CheckCircle2 className="w-3 h-3" /> },
    medium: { label: "Media", cls: "bg-amber-50 text-amber-700 border-amber-200",  icon: <Minus className="w-3 h-3" /> },
    low:    { label: "Baja", cls: "bg-red-50 text-red-700 border-red-200",         icon: <AlertCircle className="w-3 h-3" /> },
  };
  const c = map[normalizeConfidence(confidence)];
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${c.cls}`}>
      {c.icon}{c.label}
    </span>
  );
}

// ── Main panel ────────────────────────────────────────────────────
export default function DiagnosisPanel({ diagnosis, onClose }: Props) {
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);

  const scoreEntries = Object.entries(diagnosis.scores || {});
  const findings      = diagnosis.findings || [];
  const recommendations = diagnosis.recommendations || [];
  const hasNarrative  = diagnosis.narrative_md && diagnosis.narrative_md.trim().length > 0;

  // Overall score: average of dimension scores
  const overallScore =
    scoreEntries.length > 0
      ? scoreEntries.reduce((sum, [, d]) => sum + (d.score ?? 0), 0) / scoreEntries.length
      : 0;

  return (
    <div
      className="absolute top-0 right-0 h-full bg-warm-50 border-l border-warm-200 shadow-warm-md z-20 flex flex-col"
      style={{ width: "clamp(380px, 62%, 760px)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-warm-200 bg-white flex-shrink-0">
        <div>
          <h2 className="font-display italic text-xl text-warm-900">Diagnóstico Organizacional</h2>
          <p className="text-xs text-warm-500 mt-0.5">
            {findings.length} hallazgos · {recommendations.length} recomendaciones
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-warm-300 rounded-md hover:bg-warm-100 text-warm-600 transition-colors">
            <FileDown className="w-3.5 h-3.5" />
            Exportar PDF
          </button>
          <button onClick={onClose} className="text-warm-400 hover:text-warm-700 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-8">

        {/* Score global */}
        <div className="text-center p-5 bg-white rounded-xl border border-warm-200">
          <p className="text-xs font-semibold text-warm-400 uppercase tracking-widest mb-1">
            Score Global
          </p>
          <p className="text-5xl font-bold text-warm-900 tabular-nums">
            {overallScore.toFixed(1)}
            <span className="text-xl text-warm-400 font-normal">/5</span>
          </p>
          <p className="text-xs text-warm-400 mt-1">
            {overallScore >= 3.8 ? "Saludable" : overallScore >= 2.5 ? "Atención recomendada" : "Intervención urgente"}
          </p>
        </div>

        {/* Narrative (markdown rendered as pre-formatted text) */}
        {hasNarrative && (
          <div>
            <h3 className="text-sm font-semibold text-warm-900 mb-3">Resumen Ejecutivo</h3>
            <div className="text-sm text-warm-700 leading-relaxed whitespace-pre-line bg-white border border-warm-200 rounded-lg px-4 py-3">
              {/* Extract first ~400 chars as executive summary until full markdown renderer is added */}
              {diagnosis.narrative_md.slice(0, 600)}
              {diagnosis.narrative_md.length > 600 && (
                <span className="text-warm-400">… (ver diagnóstico completo)</span>
              )}
            </div>
          </div>
        )}

        {/* Scores por dimensión */}
        {scoreEntries.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-warm-900 mb-3">Scores por Dimensión</h3>
            <div className="space-y-2.5">
              {scoreEntries.map(([dim, data]) => (
                <ScoreBar
                  key={dim}
                  label={dim}
                  score={data.score ?? 0}
                  avg={data.avg}
                />
              ))}
            </div>
          </div>
        )}

        {/* Hallazgos */}
        {findings.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-warm-900 mb-3">Hallazgos</h3>
            <div className="space-y-2">
              {findings.map((f) => {
                const isOpen = expandedFinding === f.id;
                const isStrength = f.type === "strength" || f.type === "fortaleza";
                return (
                  <div key={f.id} className="border border-warm-200 rounded-lg overflow-hidden bg-white">
                    <button
                      onClick={() => setExpandedFinding(isOpen ? null : f.id)}
                      className="w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-warm-50 transition-colors"
                    >
                      {isStrength ? (
                        <TrendingUp className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-warm-900 leading-snug">{f.title}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] text-warm-400 capitalize">{f.dimension}</span>
                          <ConfidenceBadge confidence={f.confidence} />
                        </div>
                      </div>
                      {isOpen
                        ? <ChevronDown className="w-4 h-4 text-warm-400 flex-shrink-0 mt-0.5" />
                        : <ChevronRight className="w-4 h-4 text-warm-400 flex-shrink-0 mt-0.5" />}
                    </button>
                    {isOpen && (
                      <div className="px-4 pb-3 pt-2 text-sm text-warm-700 border-t border-warm-100 leading-relaxed">
                        {f.description}
                        {f.node_ids?.length > 0 && (
                          <p className="text-[10px] text-warm-400 mt-2">
                            Nodos afectados: {f.node_ids.length}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Recomendaciones */}
        {recommendations.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-warm-900 mb-3 flex items-center gap-1.5">
              <Lightbulb className="w-4 h-4 text-accent" />
              Recomendaciones
            </h3>
            <div className="space-y-2.5">
              {[...recommendations]
                .sort((a, b) => (a.priority ?? 99) - (b.priority ?? 99))
                .map((r, i) => (
                  <div key={r.id ?? i} className="p-3 border border-warm-200 rounded-lg bg-white">
                    <div className="flex items-start gap-2">
                      <span className="text-xs font-bold text-accent bg-accent/10 rounded w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">
                        {r.priority ?? i + 1}
                      </span>
                      <div>
                        <p className="text-sm font-medium text-warm-900">{r.title}</p>
                        <p className="text-sm text-warm-600 mt-0.5 leading-relaxed">{r.description}</p>
                        {r.node_ids?.length > 0 && (
                          <p className="text-[10px] text-warm-400 mt-1.5">
                            Aplica a {r.node_ids.length} nodo{r.node_ids.length !== 1 ? "s" : ""}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Metadata */}
        <div className="text-xs text-warm-400 border-t border-warm-200 pt-4">
          {diagnosis.completed_at && (
            <p>
              Generado el{" "}
              {new Date(diagnosis.completed_at).toLocaleDateString("es-ES", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
