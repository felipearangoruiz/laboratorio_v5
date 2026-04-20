"use client";

import type { DiagnosisResult } from "@/lib/api";

interface Props {
  diagnosis: DiagnosisResult;
  active: string | null;
  onChange: (dim: string | null) => void;
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

export default function DimensionFilter({ diagnosis, active, onChange }: Props) {
  const dimensions = Object.keys(diagnosis.scores || {});
  if (dimensions.length === 0) return null;

  return (
    <div
      className="flex items-center gap-1.5 px-4 py-2 overflow-x-auto flex-shrink-0"
      style={{
        background: "rgba(13,13,20,0.88)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <span className="text-[10px] font-semibold text-white/25 uppercase tracking-widest mr-1 flex-shrink-0">
        Dimensión
      </span>

      <button
        onClick={() => onChange(null)}
        className={`flex-shrink-0 px-3 py-1 text-xs font-medium rounded-full transition-colors ${
          active === null
            ? "bg-white/15 text-white"
            : "text-white/40 hover:text-white/70 hover:bg-white/8"
        }`}
      >
        Todas
      </button>

      {dimensions.map((dim) => {
        const score   = diagnosis.scores[dim]?.score ?? 0;
        const tension = Math.round((1 - Math.min(score, 5) / 5) * 100);
        const dotColor =
          tension <= 40 ? "bg-emerald-500" : tension <= 70 ? "bg-amber-500" : "bg-red-500";
        const isActive = active === dim;

        return (
          <button
            key={dim}
            onClick={() => onChange(isActive ? null : dim)}
            className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-full transition-colors ${
              isActive
                ? "bg-white/15 text-white"
                : "text-white/40 hover:text-white/70 hover:bg-white/8"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
            {dimLabel(dim)}
          </button>
        );
      })}
    </div>
  );
}
