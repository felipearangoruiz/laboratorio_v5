"use client";

import { X, TrendingUp, TrendingDown, ArrowRight } from "lucide-react";
import type { DiagnosisResult } from "@/lib/api";

interface Props {
  nodeId: string;
  nodeName: string;
  diagnosis: DiagnosisResult;
  onClose: () => void;
  onViewNarrative: () => void;
}

const DIM_LABELS: Record<string, string> = {
  liderazgo:    "Liderazgo",
  comunicacion: "Comunicación",
  cultura:      "Cultura",
  procesos:     "Procesos",
  poder:        "Poder",
  economia:     "Economía",
  operacion:    "Operación",
  mision:       "Misión",
};

function dimLabel(key: string): string {
  return DIM_LABELS[key.toLowerCase()] ?? key;
}

export default function AnalysisNodePanel({
  nodeId,
  nodeName,
  diagnosis,
  onClose,
  onViewNarrative,
}: Props) {
  // Per-dimension scores for this node vs org average
  const dimScores = Object.entries(diagnosis.scores || {})
    .map(([dim, data]) => ({
      dim,
      nodeScore: data.node_scores?.[nodeId] ?? null,
      orgAvg:    data.avg ?? 0,
    }))
    .filter((d) => d.nodeScore !== null) as {
      dim: string;
      nodeScore: number;
      orgAvg: number;
    }[];

  // Top 2 findings for this node
  const nodeFindings = (diagnosis.findings || [])
    .filter((f) => f.node_ids?.includes(nodeId))
    .slice(0, 2);

  // Overall node score (average across dimensions)
  const overallScore =
    dimScores.length > 0
      ? dimScores.reduce((sum, d) => sum + d.nodeScore, 0) / dimScores.length
      : null;

  const overallColor =
    overallScore === null
      ? "text-warm-900"
      : overallScore >= 3.8
      ? "text-emerald-600"
      : overallScore >= 2.5
      ? "text-amber-600"
      : "text-red-600";

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

        {/* Overall score */}
        {overallScore !== null && (
          <div className="text-center p-4 bg-white rounded-xl border border-warm-200">
            <p className="text-[10px] font-semibold text-warm-400 uppercase tracking-widest mb-1">
              Score Promedio
            </p>
            <p className={`text-4xl font-bold tabular-nums ${overallColor}`}>
              {overallScore.toFixed(1)}
              <span className="text-base text-warm-400 font-normal">/5</span>
            </p>
            <p className="text-[10px] text-warm-400 mt-1">
              {overallScore >= 3.8
                ? "Saludable"
                : overallScore >= 2.5
                ? "Atención recomendada"
                : "Intervención urgente"}
            </p>
          </div>
        )}

        {/* Per-dimension score bars */}
        {dimScores.length > 0 && (
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
                      <div
                        className={`h-full rounded-full transition-all ${barColor}`}
                        style={{ width: `${pct}%` }}
                      />
                      {/* Org average marker */}
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
        )}

        {/* Top findings for this node */}
        {nodeFindings.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-warm-700 mb-2.5">Hallazgos relacionados</p>
            <div className="space-y-2">
              {nodeFindings.map((f) => {
                const isStrength = f.type === "strength" || f.type === "fortaleza";
                return (
                  <div key={f.id} className="p-2.5 border border-warm-200 rounded-lg bg-white">
                    <div className="flex items-start gap-2">
                      {isStrength ? (
                        <TrendingUp className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                      ) : (
                        <TrendingDown className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-warm-900 leading-snug">{f.title}</p>
                        <p className="text-[10px] text-warm-400 mt-0.5 capitalize">{dimLabel(f.dimension)}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
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
