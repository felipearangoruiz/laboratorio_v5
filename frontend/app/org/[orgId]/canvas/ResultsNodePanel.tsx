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
import type { DiagnosisResult, DiagnosisFinding } from "@/lib/api";

interface Props {
  nodeId: string;
  nodeName: string;
  diagnosis: DiagnosisResult;
  onClose: () => void;
  /** Sprint 5.C feature (iii) — acepta un findingId opcional para
   *  deep-link: si se pasa, NarrativePanel abre con scroll + expand
   *  automático hacia ese finding. Sin argumento, abre al inicio. */
  onViewNarrative: (findingId?: string) => void;
}

// ── Helpers ───────────────────────────────────────────────────────
const DIM_LABELS: Record<string, string> = {
  liderazgo:       "Liderazgo",
  comunicacion:    "Comunicación",
  cultura:         "Cultura",
  procesos:        "Procesos",
  poder:           "Poder",
  economia:        "Economía",
  operacion:       "Operación",
  mision:          "Misión",
  centralizacion:  "Centralización",
  cuellos_botella: "Cuellos de botella",
  alineacion:      "Alineación",
  bienestar:       "Bienestar",
  recursos:        "Recursos",
  vision:          "Visión",
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

/** Normalize confidence from string or float to "high"|"medium"|"low" */
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

/** Get the primary dimension for a finding (supports both formats) */
function findingPrimaryDim(f: DiagnosisFinding): string {
  if (f.dimensions && f.dimensions.length > 0) return f.dimensions[0];
  return f.dimension ?? "";
}

/** Labels for new motor finding types */
const TYPE_LABELS: Record<string, string> = {
  observacion: "Observación",
  patron:      "Patrón",
  inferencia:  "Inferencia",
  hipotesis:   "Hipótesis",
  strength:    "Fortaleza",
  fortaleza:   "Fortaleza",
  risk:        "Riesgo",
  riesgo:      "Riesgo",
};

function ConfidenceBadge({ confidence }: { confidence: string | number }) {
  const norm = normalizeConfidence(confidence);
  const map: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    high:   { label: "Alta",  cls: "bg-green-50 text-green-700 border-green-200",  icon: <CheckCircle2 className="w-3 h-3" /> },
    medium: { label: "Media", cls: "bg-amber-50 text-amber-700 border-amber-200",  icon: <Minus className="w-3 h-3" /> },
    low:    { label: "Baja",  cls: "bg-red-50 text-red-700 border-red-200",        icon: <AlertCircle className="w-3 h-3" /> },
  };
  const c = map[norm];
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
                const primaryDim = findingPrimaryDim(f);
                const typeLabel  = TYPE_LABELS[f.type] ?? f.type;

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
                          {primaryDim && (
                            <span
                              className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium capitalize ${dimColor(primaryDim)}`}
                            >
                              {dimLabel(primaryDim)}
                            </span>
                          )}
                          {/* All dimensions (new motor) */}
                          {f.dimensions && f.dimensions.length > 1 && f.dimensions.slice(1).map((d, i) => (
                            <span
                              key={i}
                              className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium capitalize bg-warm-100 text-warm-600"
                            >
                              {dimLabel(d)}
                            </span>
                          ))}
                          <ConfidenceBadge confidence={f.confidence} />
                          {/* Type label for new motor types */}
                          {typeLabel && !["strength", "fortaleza", "risk", "riesgo"].includes(f.type) && (
                            <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-accent/10 text-accent capitalize">
                              {typeLabel}
                            </span>
                          )}
                        </div>
                        {/* Sprint 5.C feature (iii) — deep-link al panel
                            narrativo expandido en este finding concreto. */}
                        <button
                          type="button"
                          onClick={() => onViewNarrative(f.id)}
                          className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-accent hover:text-accent/70 transition-colors"
                          title="Abrir diagnóstico completo en este hallazgo"
                        >
                          Ver en diagnóstico
                          <ArrowRight className="w-3 h-3" />
                        </button>
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
                      {(r.horizon || r.impact || r.effort) && (
                        <div className="flex items-center gap-3 mt-1.5 text-[10px] text-warm-400">
                          {r.horizon && (
                            <span>Horizonte: <span className="font-medium text-warm-600 capitalize">{r.horizon}</span></span>
                          )}
                          {r.impact && (
                            <span>Impacto: <span className="font-medium text-warm-600 capitalize">{r.impact}</span></span>
                          )}
                          {r.effort && (
                            <span>Esfuerzo: <span className="font-medium text-warm-600 capitalize">{r.effort}</span></span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTA — open full narrative */}
        <button
          onClick={() => onViewNarrative()}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-warm-900 text-white text-xs font-semibold rounded-xl hover:bg-warm-800 transition-colors"
        >
          Ver diagnóstico completo
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
