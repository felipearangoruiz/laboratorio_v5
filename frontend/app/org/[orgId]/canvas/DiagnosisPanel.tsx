"use client";

import { useState } from "react";
import {
  X,
  FileDown,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  Lightbulb,
  Network,
} from "lucide-react";

interface Props {
  diagnosis: any;
  onClose: () => void;
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const color =
    score >= 70
      ? "bg-emerald-500"
      : score >= 50
      ? "bg-amber-500"
      : "bg-red-500";

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-700 w-36 truncate">{label}</span>
      <div className="flex-1 h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-sm font-semibold text-gray-900 w-12 text-right">
        {score}
      </span>
    </div>
  );
}

export default function DiagnosisPanel({ diagnosis, onClose }: Props) {
  const [expandedDim, setExpandedDim] = useState<string | null>(null);

  const scores = diagnosis.scores || {};
  const narrative = diagnosis.narrative || {};
  const network = diagnosis.network_metrics || {};
  const dims = scores.dimensions || [];
  const hallazgos = narrative.hallazgos || [];
  const patrones = narrative.patrones_cruzados || [];
  const recos = narrative.recomendaciones || [];

  const prioLabels: Record<string, { label: string; color: string }> = {
    corto_plazo: { label: "Corto plazo", color: "bg-red-50 text-red-700" },
    mediano_plazo: { label: "Mediano plazo", color: "bg-amber-50 text-amber-700" },
    largo_plazo: { label: "Largo plazo", color: "bg-blue-50 text-blue-700" },
  };

  return (
    <div className="absolute top-0 right-0 h-full bg-white border-l border-gray-200 shadow-xl z-20 flex flex-col"
      style={{ width: "clamp(400px, 65%, 800px)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            Diagnóstico Organizacional
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {scores.total_responses || 0} entrevistas analizadas
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <FileDown className="w-3.5 h-3.5" />
            Exportar PDF
          </button>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-8">
        {/* Score global */}
        <div className="text-center p-5 bg-gray-50 rounded-xl">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Score Global
          </p>
          <p className="text-4xl font-bold text-gray-900 mt-1">
            {scores.overall || 0}
            <span className="text-lg text-gray-400">/100</span>
          </p>
        </div>

        {/* Resumen ejecutivo */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-2">
            Resumen Ejecutivo
          </h3>
          <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
            {narrative.resumen_ejecutivo || "Sin resumen disponible."}
          </p>
        </div>

        {/* Scores por dimensión */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Scores por Dimensión
          </h3>
          <div className="space-y-2.5">
            {dims.map((d: any) => (
              <ScoreBar key={d.id} label={d.label} score={d.score} />
            ))}
          </div>
        </div>

        {/* Hallazgos por dimensión */}
        {hallazgos.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              Hallazgos por Dimensión
            </h3>
            <div className="space-y-2">
              {hallazgos.map((h: any, i: number) => {
                const isExpanded = expandedDim === `h-${i}`;
                return (
                  <div
                    key={i}
                    className="border border-gray-200 rounded-lg overflow-hidden"
                  >
                    <button
                      onClick={() =>
                        setExpandedDim(isExpanded ? null : `h-${i}`)
                      }
                      className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-gray-50"
                    >
                      {h.tipo === "fortaleza" ? (
                        <TrendingUp className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-500 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {h.titulo}
                        </p>
                        <p className="text-[10px] text-gray-500">
                          {h.dimension}
                        </p>
                      </div>
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )}
                    </button>
                    {isExpanded && (
                      <div className="px-3 pb-3 text-sm text-gray-600 border-t border-gray-100 pt-2">
                        {h.descripcion}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Patrones cruzados */}
        {patrones.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-1.5">
              <Network className="w-4 h-4" />
              Patrones Cruzados
            </h3>
            <div className="space-y-3">
              {patrones.map((p: any, i: number) => (
                <div
                  key={i}
                  className="p-3 bg-purple-50 border border-purple-100 rounded-lg"
                >
                  <p className="text-sm font-medium text-purple-900">
                    {p.titulo}
                  </p>
                  <p className="text-xs text-purple-700 mt-0.5">
                    {(p.dimensiones_involucradas || []).join(" + ")}
                  </p>
                  <p className="text-sm text-purple-800 mt-1.5">
                    {p.descripcion}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recomendaciones */}
        {recos.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-1.5">
              <Lightbulb className="w-4 h-4" />
              Recomendaciones
            </h3>
            <div className="space-y-3">
              {recos.map((r: any, i: number) => {
                const prio = prioLabels[r.prioridad] || prioLabels.mediano_plazo;
                return (
                  <div
                    key={i}
                    className="p-3 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-gray-900">
                        {r.titulo}
                      </p>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-medium rounded-full flex-shrink-0 ${prio.color}`}
                      >
                        {prio.label}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      {r.descripcion}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Network metrics */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-2">
            Métricas de Red
          </h3>
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-lg font-bold text-gray-900">
                {network.total_nodes || 0}
              </p>
              <p className="text-[10px] text-gray-500">Nodos</p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-lg font-bold text-gray-900">
                {network.depth || 0}
              </p>
              <p className="text-[10px] text-gray-500">Profundidad</p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-lg font-bold text-gray-900">
                {network.isolated || 0}
              </p>
              <p className="text-[10px] text-gray-500">Aislados</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
