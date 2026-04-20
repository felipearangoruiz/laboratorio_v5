"use client";

import {
  X,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  CheckCircle2,
  Minus,
  AlertCircle,
} from "lucide-react";
import type { DiagnosisResult } from "@/lib/api";

interface Props {
  nodeId: string;
  nodeName: string;
  diagnosis: DiagnosisResult;
  onClose: () => void;
  onViewNarrative: () => void;
}

// ── Helpers ───────────────────────────────────────────────────────
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

const DIM_COLORS: Record<string, string> = {
  liderazgo:    "bg-purple-50 text-purple-700",
  comunicacion: "bg-blue-50 text-blue-700",
  cultura:      "bg-pink-50 text-pink-700",
  procesos:     "bg-orange-50 text-orange-700",
  poder:        "bg-red-50 text-red-700",
  economia:     "bg-emerald-50 text-emerald-700",
  operacion:    "bg-cyan-50 text-cyan-700",
  mision:       "bg-indigo-50 text-indigo-700",
};

function dimLabel(key: string): string {
  return DIM_LABELS[key.toLowerCase()] ?? key;
}

function dimColor(key: string): string {
  return DIM_COLORS[key.toLowerCase()] ?? "bg-warm-100 text-warm-600";
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const map: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    high:   { label: "Alta",  cls: "bg-green-50 text-green-700 border-green-200",  icon: <CheckCircle2 className="w-3 h-3" /> },
    medium: { label: "Media", cls: "bg-amber-50 text-amber-700 border-amber-200",  icon: <Minus className="w-3 h-3" /> },
    low:    { label: "Baja",  cls: "bg-red-50 text-red-700 border-red-200",        icon: <AlertCircle className="w-3 h-3" /> },
  };
  const c = map[confidence] ?? map.medium;
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${c.cls}`}>
      {c.icon}{c.label}
    </span>
  );
}

// ── Main panel ────────────────────────────────────────────────────
export default function ResultsNodePanel({
  nodeId,
  nodeName,
  diagnosis,
  onClose,
  onViewNarrative,
}: Props) {
  const nodeFindings = (diagnosis.findings || []).filter(
    (f) => f.node_ids?.includes(nodeId)
  );
  const nodeRecs = (diagnosis.recommendations || [])
    .filter((r) => r.node_ids?.includes(nodeId))
    .sort((a, b) => (a.priority ?? 99) - (b.priority ?? 99));

  return (
    <div
      className="absolute top-0 right-0 h-full bg-warm-50 border-l border-warm-200 shadow-warm-md z-20 flex flex-col"
      style={{ width: "clamp(300px, 38%, 440px)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-warm-200 bg-white flex-shrink-0">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold text-warm-400 uppercase tracking-widest">
            Resultados
          </p>
          <h3 className="font-semibold text-warm-900 text-sm mt-0.5 truncate">{nodeName}</h3>
        </div>
        <button
          onClick={onClose}
          className="text-warm-400 hover:text-warm-700 transition-colors flex-shrink-0 ml-3"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">

        {/* Hallazgos */}
        <div>
          <p className="text-xs font-semibold text-warm-700 mb-2.5">
            Hallazgos
            {nodeFindings.length > 0 && (
              <span className="ml-1.5 text-warm-400 font-normal">({nodeFindings.length})</span>
            )}
          </p>

          {nodeFindings.length > 0 ? (
            <div className="space-y-2">
              {nodeFindings.map((f) => {
                const isStrength = f.type === "strength" || f.type === "fortaleza";
                return (
                  <div
                    key={f.id}
                    className="p-3 border border-warm-200 rounded-lg bg-white"
                  >
                    <div className="flex items-start gap-2">
                      {isStrength ? (
                        <TrendingUp className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                      ) : (
                        <TrendingDown className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-warm-900 leading-snug mb-1">
                          {f.title}
                        </p>
                        <p className="text-[11px] text-warm-600 leading-relaxed line-clamp-2 mb-1.5">
                          {f.description}
                        </p>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span
                            className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium capitalize ${dimColor(f.dimension)}`}
                          >
                            {dimLabel(f.dimension)}
                          </span>
                          <ConfidenceBadge confidence={f.confidence} />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-warm-400 text-center py-4">
              Sin hallazgos para este nodo
            </p>
          )}
        </div>

        {/* Recomendaciones */}
        {nodeRecs.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-warm-700 mb-2.5">
              Recomendaciones
              <span className="ml-1.5 text-warm-400 font-normal">({nodeRecs.length})</span>
            </p>
            <div className="space-y-2">
              {nodeRecs.map((r, i) => (
                <div
                  key={r.id ?? i}
                  className="p-3 border border-warm-200 rounded-lg bg-white"
                >
                  <div className="flex items-start gap-2">
                    <span className="text-xs font-bold text-accent bg-accent/10 rounded w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">
                      {r.priority ?? i + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-warm-900 leading-snug">
                        {r.title}
                      </p>
                      <p className="text-[11px] text-warm-600 mt-0.5 leading-relaxed">
                        {r.description}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTA — open full narrative */}
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
