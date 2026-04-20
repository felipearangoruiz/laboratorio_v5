"use client";

import { useState } from "react";
import { Loader2, Lock, Sparkles, CheckCircle2 } from "lucide-react";
import { getDiagnosisInput, ApiError } from "@/lib/api";

interface Props {
  orgId: string;
  completedNodes: number;
  totalNodes: number;
  thresholdMet: boolean;
  onInitiated: () => void;
}

const MIN_NODES    = 5;
const PCT_REQUIRED = 40;

function Condition({ met, label }: { met: boolean; label: string }) {
  return (
    <div className={`flex items-center gap-2 text-xs ${met ? "text-warm-700" : "text-warm-400"}`}>
      {met ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
      ) : (
        <div className="w-3.5 h-3.5 rounded-full border-2 border-warm-300 flex-shrink-0" />
      )}
      {label}
    </div>
  );
}

export default function DiagnosisGate({
  orgId,
  completedNodes,
  totalNodes,
  thresholdMet,
  onInitiated,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const pct      = totalNodes > 0 ? Math.round((completedNodes / totalNodes) * 100) : 0;
  const meetsMin = completedNodes >= MIN_NODES;
  const meetsPct = pct >= PCT_REQUIRED;

  async function handleGenerate() {
    setLoading(true);
    setError("");
    try {
      await getDiagnosisInput(orgId);
      onInitiated();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Error al preparar los datos para el diagnóstico.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="absolute top-0 right-0 h-full bg-warm-50 border-l border-warm-200 z-20 flex flex-col"
      style={{ width: "clamp(300px, 38%, 440px)" }}
    >
      {/* Header */}
      <div className="flex items-center px-4 py-3 border-b border-warm-200 bg-white flex-shrink-0">
        <div>
          <p className="text-[10px] font-semibold text-warm-400 uppercase tracking-widest">
            Resultados
          </p>
          <h3 className="font-semibold text-warm-900 text-sm mt-0.5">Generar diagnóstico</h3>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-6 space-y-6">

        {/* Progress card */}
        <div className="bg-white rounded-xl border border-warm-200 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-warm-700">Cobertura de recolección</span>
            <span
              className={`text-xs font-bold tabular-nums ${
                meetsPct ? "text-emerald-600" : "text-warm-900"
              }`}
            >
              {pct}%
            </span>
          </div>

          {/* Progress bar with threshold marker */}
          <div className="h-2 bg-warm-100 rounded-full overflow-hidden relative">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                meetsPct ? "bg-emerald-500" : "bg-accent"
              }`}
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
            {/* 40% threshold line */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-warm-500/40"
              style={{ left: "40%" }}
              title="Umbral mínimo: 40%"
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-warm-500">
            <span>
              <span className="font-semibold text-warm-900">{completedNodes}</span>
              {" "}de{" "}
              <span className="font-semibold text-warm-900">{totalNodes}</span>
              {" "}nodos con entrevista completada
            </span>
            <span className="text-warm-400">umbral: {PCT_REQUIRED}%</span>
          </div>
        </div>

        {/* Conditions checklist */}
        <div className="space-y-2.5">
          <p className="text-xs font-semibold text-warm-600">Condiciones para el diagnóstico</p>
          <Condition
            met={meetsPct}
            label={`Alcanzar el ${PCT_REQUIRED}% de cobertura (actual: ${pct}%)`}
          />
          <Condition
            met={meetsMin}
            label={`Mínimo ${MIN_NODES} nodos respondidos (actual: ${completedNodes})`}
          />
        </div>

        {/* Explanation when locked */}
        {!thresholdMet && (
          <div className="bg-warm-100/60 rounded-lg px-3 py-3">
            <p className="text-xs text-warm-600 leading-relaxed">
              Cuando alcances el umbral ({PCT_REQUIRED}%, mínimo {MIN_NODES} nodos), podrás generar el
              diagnóstico completo con análisis por IA de las 8 dimensiones organizacionales.
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
            {error}
          </p>
        )}

        {/* CTA button */}
        <button
          onClick={handleGenerate}
          disabled={!thresholdMet || loading}
          className={`w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            thresholdMet && !loading
              ? "bg-warm-900 text-white hover:bg-warm-800 active:scale-[0.98]"
              : "bg-warm-200 text-warm-400 cursor-not-allowed"
          }`}
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Preparando datos…
            </>
          ) : !thresholdMet ? (
            <>
              <Lock className="w-4 h-4" />
              Generar diagnóstico
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generar diagnóstico
            </>
          )}
        </button>

        {thresholdMet && !loading && (
          <p className="text-[11px] text-warm-400 text-center -mt-2">
            El procesamiento es externo y puede tardar unos minutos.
          </p>
        )}
      </div>
    </div>
  );
}
