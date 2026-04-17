"use client";

import { Lock } from "lucide-react";

interface LayerSelectorProps {
  active: string;
  onChange: (layer: string) => void;
  hasNodes: boolean;
}

export default function LayerSelector({
  active,
  onChange,
  hasNodes,
}: LayerSelectorProps) {
  const layers = [
    { id: "estructura", label: "Estructura", locked: false },
    { id: "recoleccion", label: "Recolección", locked: !hasNodes },
    { id: "analisis", label: "Análisis", locked: true },
    { id: "resultados", label: "Resultados", locked: true },
  ];

  return (
    <div className="h-11 border-b border-gray-200 bg-white flex items-center px-4 gap-1">
      {layers.map((layer) => {
        const isActive = active === layer.id;
        const isLocked = layer.locked;
        const tooltip = isLocked
          ? layer.id === "recoleccion"
            ? "Crea tu estructura primero"
            : "Completa las fases anteriores"
          : undefined;

        return (
          <button
            key={layer.id}
            onClick={() => !isLocked && onChange(layer.id)}
            disabled={isLocked}
            className={`relative px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              isActive
                ? "bg-gray-900 text-white"
                : isLocked
                ? "text-gray-400 cursor-not-allowed"
                : "text-gray-600 hover:bg-gray-100"
            }`}
            title={tooltip}
          >
            <span className="flex items-center gap-1.5">
              {layer.label}
              {isLocked && <Lock className="w-3 h-3" />}
            </span>
          </button>
        );
      })}

      {hasNodes && active === "estructura" && (
        <div className="ml-auto text-xs text-gray-400">
          Arrastra desde el borde de un nodo para conectar
        </div>
      )}
    </div>
  );
}
