"use client";

import { Lock } from "lucide-react";

interface LayerSelectorProps {
  active: string;
  onChange: (layer: string) => void;
  hasNodes: boolean;
  thresholdMet: boolean;
  hasDiagnosis: boolean;
}

export default function LayerSelector({
  active,
  onChange,
  hasNodes,
  thresholdMet,
  hasDiagnosis,
}: LayerSelectorProps) {
  const layers = [
    { id: "estructura",  label: "Estructura",  locked: false },
    { id: "recoleccion", label: "Recolección", locked: !hasNodes },
    { id: "analisis",    label: "Análisis",    locked: !thresholdMet },
    { id: "resultados",  label: "Resultados",  locked: !hasDiagnosis },
  ];

  const tooltips: Record<string, string> = {
    recoleccion: "Crea tu estructura primero",
    analisis:    "Alcanza el umbral de recolección primero",
    resultados:  "Genera tu diagnóstico primero",
  };

  return (
    <div
      className="h-11 flex items-center px-4 gap-0.5 border-b"
      style={{
        background: "rgba(13,13,20,0.92)",
        backdropFilter: "blur(8px)",
        borderBottomColor: "rgba(255,255,255,0.08)",
      }}
    >
      {layers.map((layer) => {
        const isActive = active === layer.id;
        const isLocked = layer.locked;

        return (
          <button
            key={layer.id}
            onClick={() => !isLocked && onChange(layer.id)}
            disabled={isLocked}
            title={isLocked ? tooltips[layer.id] : undefined}
            className={`relative px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              isActive
                ? "text-white"
                : isLocked
                ? "text-white/25 cursor-not-allowed"
                : "text-white/50 hover:text-white/80"
            }`}
          >
            <span className="flex items-center gap-1.5">
              {layer.label}
              {isLocked && <Lock className="w-3 h-3" />}
            </span>
            {/* Active underline */}
            {isActive && (
              <span className="absolute bottom-0 left-4 right-4 h-[2px] rounded-full bg-[#C2410C]" />
            )}
          </button>
        );
      })}

      {hasNodes && active === "estructura" && (
        <div className="ml-auto text-[11px] text-white/30 font-medium">
          Arrastra desde el borde para conectar
        </div>
      )}
    </div>
  );
}
