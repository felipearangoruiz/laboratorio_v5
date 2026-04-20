"use client";

import { useEffect, useState } from "react";
import { X, TrendingUp, TrendingDown, ArrowRight, Loader2 } from "lucide-react";
import { getNodeAnalysis, type NodeAnalysisRead, type DiagnosisResult } from "@/lib/api";

interface Props {
  orgId: string;
  nodeId: string;
  nodeName: string;
  diagnosis: DiagnosisResult;
  onClose: () => void;
  onViewNarrative: () => void;
}

const DIM_LABELS: Record<string, string> = {
  // 8 dimensions PRD v2
  liderazgo:       "Liderazgo",
  comunicacion:    "Comunicación",
  cultura:         "Cultura",
  procesos:        "Procesos",
  poder:           "Poder",
  economia:        "Economía",
  operacion:       "Operación",
  mision:          "Misión",
  // New motor analysis dimensions
  centralizacion:  "Centralización",
  cuellos_botella: "Cuellos de botella",
  alineacion:      "Alineación",
  bienestar:       "Bienestar",
  recursos:        "Recursos",
  vision:          "Visión",
};

function dimLabel(key: string): string {
  return DIM_LABELS[key.toLowerCase()] ?? key;
}

// ── Confidence bar (float 0–1) ────────────────────────────────────
function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(Math.min(100, Math.max(0, value * 100)));
  const color =
    value >= 0.7 ? "bg-emerald-500" : value >= 0.45 ? "bg-amber-500" : "bg-red-400";
  const label =
    value >= 0.7 ? "Alta" : value >= 0.45 ? "Media" : "Baja";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-warm-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-semibold text-warm-500 tabular-nums w-10 text-right">
        {label} {pct}%
      </span>
    </div>
  );
}

export default function AnalysisNodePanel({
  orgId,
  nodeId,
  nodeName,
  diagnosis,
  onClose,
  onViewNarrative,
}: Props) {
  const [nodeAnalysis, setNodeAnalysis] = useState<NodeAnalysisRead | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setNodeAnalysis(null);
    getNodeAnalysis(orgId, nodeId)
      .then((data) => setNodeAnalysis(data))
      .catch(() => setNodeAnalysis(null))
      .finally(() => setLoading(false));
  }, [orgId, nodeId]);

  // Fallback: legacy per-dim scores from diagnosis.scores
  const dimScores = Object.entries(diagnosis.scores || {})
    .map(([dim, data]) => ({
      dim,
      nodeScore: data.node_scores?.[nodeId] ?? null,
      orgAvg: data.avg ?? 0,
    }))
    .filter((d) => d.nodeScore !== null) as { dim: string; nodeScore: number; orgAvg: number }[];

  const overallScore =
    dimScores.length > 0
      ? dimScores.reduce((sum, d) => sum + d.nodeScore, 0) / dimScores.length
      : null;

  return (
    <div
      className="absolute top-0 right-0 h-full bg-warm-50 border-l border-warm-200 shadow-warm-md z-20 flex flex-col"
      style={{ width: "clamp(300px, 36%, 420px)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-warm-200 bg-white flex-shrink-0">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold text-warm-400 uppercase tracking-widest">Análisis</p>
          <h3 className="font-semibold text-warm-900 text-sm mt-0.5 truncate">{nodeName}</h3>
        </div>
        <button onClick={onClose} className="text-warm-400 hover:text-warm-700 transition-colors flex-shrink-0 ml-3">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">

        {loading ? (
          <div className="flex flex-col items-center justify-center py-10 text-warm-400 gap-2">
            <Loader2 className="w-5 h-5 animate-spin" />
            <p className="text-xs">Cargando análisis…</p>
          </div>
        ) : nodeAnalysis ? (
          <>
            {/* Signals tension */}
            {nodeAnalysis.signals_tension.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-warm-700 mb-2 flex items-center gap-1.5">
                  <TrendingDown className="w-3.5 h-3.5 text-red-500" />
                  Tensiones detectadas
                </p>
                <ul className="space-y-1.5">
                  {nodeAnalysis.signals_tension.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-[11px] text-warm-700 leading-snug">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Signals positive */}
            {nodeAnalysis.signals_positive.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-warm-700 mb-2 flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
                  Señales positivas
                </p>
                <ul className="space-y-1.5">
                  {nodeAnalysis.signals_positive.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-[11px] text-warm-700 leading-snug">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Themes */}
            {nodeAnalysis.themes.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-warm-700 mb-2">Temas recurrentes</p>
                <div className="flex flex-wrap gap-1.5">
                  {nodeAnalysis.themes.map((t, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-warm-100 text-warm-700 text-[10px] font-medium rounded-full capitalize"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Dimensions touched */}
            {nodeAnalysis.dimensions_touched.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-warm-700 mb-2">Dimensiones afectadas</p>
                <div className="flex flex-wrap gap-1.5">
                  {nodeAnalysis.dimensions_touched.map((d, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-accent/10 text-accent text-[10px] font-semibold rounded-full capitalize"
                    >
                      {dimLabel(d)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Key quotes */}
            {nodeAnalysis.key_quotes.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-warm-700 mb-2">Citas clave</p>
                <div className="space-y-2">
                  {nodeAnalysis.key_quotes.map((q, i) => (
                    <blockquote
                      key={i}
                      className="border-l-2 border-accent/40 pl-3 italic text-[11px] text-warm-600 leading-relaxed"
                    >
                      "{q}"
                    </blockquote>
                  ))}
                </div>
              </div>
            )}

            {/* Confidence */}
            <div>
              <p className="text-xs font-semibold text-warm-700 mb-2">Confianza del análisis</p>
              <ConfidenceBar value={nodeAnalysis.confidence} />
            </div>

            {/* Evidence type / emotional intensity metadata */}
            {(nodeAnalysis.evidence_type || nodeAnalysis.emotional_intensity) && (
              <div className="flex items-center gap-3 text-[10px] text-warm-400">
                {nodeAnalysis.evidence_type && (
                  <span>
                    Evidencia:{" "}
                    <span className="font-medium text-warm-600 capitalize">{nodeAnalysis.evidence_type}</span>
                  </span>
                )}
                {nodeAnalysis.emotional_intensity && (
                  <span>
                    Intensidad:{" "}
                    <span className="font-medium text-warm-600 capitalize">{nodeAnalysis.emotional_intensity}</span>
                  </span>
                )}
              </div>
            )}
          </>
        ) : (
          /* No analysis data — show legacy scores fallback or empty state */
          <>
            {overallScore !== null ? (
              <>
                {/* Legacy overall score */}
                <div className="text-center p-4 bg-white rounded-xl border border-warm-200">
                  <p className="text-[10px] font-semibold text-warm-400 uppercase tracking-widest mb-1">
                    Score Promedio
                  </p>
                  <p className={`text-4xl font-bold tabular-nums ${
                    overallScore >= 3.8 ? "text-emerald-600" : overallScore >= 2.5 ? "text-amber-600" : "text-red-600"
                  }`}>
                    {overallScore.toFixed(1)}
                    <span className="text-base text-warm-400 font-normal">/5</span>
                  </p>
                  <p className="text-[10px] text-warm-400 mt-1">
                    {overallScore >= 3.8 ? "Saludable" : overallScore >= 2.5 ? "Atención recomendada" : "Intervención urgente"}
                  </p>
                </div>

                {/* Legacy per-dim bars */}
                <div>
                  <p className="text-xs font-semibold text-warm-700 mb-2.5">Score por dimensión</p>
                  <div className="space-y-2.5">
                    {dimScores.map(({ dim, nodeScore, orgAvg }) => {
                      const pct    = Math.round(Math.min(100, Math.max(0, nodeScore * 20)));
                      const avgPct = Math.round(Math.min(100, Math.max(0, orgAvg * 20)));
                      const diff   = nodeScore - orgAvg;
                      const barColor =
                        nodeScore >= 3.8 ? "bg-emerald-500" : nodeScore >= 2.5 ? "bg-amber-500" : "bg-red-500";
                      return (
                        <div key={dim}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-[11px] text-warm-600 capitalize">{dimLabel(dim)}</span>
                            <div className="flex items-center gap-1.5">
                              {diff > 0.05 ? (
                                <TrendingUp className="w-3 h-3 text-emerald-500" />
                              ) : diff < -0.05 ? (
                                <TrendingDown className="w-3 h-3 text-red-500" />
                              ) : null}
                              <span className="text-[11px] font-semibold text-warm-900 tabular-nums">
                                {nodeScore.toFixed(1)}
                              </span>
                              <span className="text-[10px] text-warm-400 tabular-nums">
                                ({diff > 0 ? "+" : ""}{diff.toFixed(1)} vs org)
                              </span>
                            </div>
                          </div>
                          <div className="h-1.5 bg-warm-100 rounded-full overflow-hidden relative">
                            <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
                            <div
                              className="absolute top-0 bottom-0 w-px bg-warm-400/50"
                              style={{ left: `${avgPct}%` }}
                              title={`Promedio org: ${orgAvg.toFixed(1)}`}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-10 space-y-2">
                <p className="text-xs font-semibold text-warm-600">Sin datos de análisis</p>
                <p className="text-[11px] text-warm-400 leading-relaxed max-w-[220px] mx-auto">
                  Este nodo aún no tiene análisis del motor. Corre el pipeline para generar resultados.
                </p>
              </div>
            )}
          </>
        )}

        {/* CTA — open narrative panel */}
        <button
          onClick={onViewNarrative}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-warm-900 text-white text-xs font-semibold rounded-xl hover:bg-warm-800 transition-colors"
        >
          Ver diagnóstico completo
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
