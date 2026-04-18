"use client";

import type { OrgInfo } from "./page";
import { ArrowLeft, ArrowRight } from "lucide-react";

const ORG_TYPES = [
  { value: "empresa", label: "Empresa" },
  { value: "ong", label: "ONG / Sin ánimo de lucro" },
  { value: "equipo", label: "Equipo de proyecto" },
  { value: "otro", label: "Otro" },
];

const SIZE_RANGES = [
  { value: "1-10",   label: "1–10 personas" },
  { value: "11-50",  label: "11–50 personas" },
  { value: "51-200", label: "51–200 personas" },
  { value: "200+",   label: "Más de 200" },
];

interface Props {
  orgInfo: OrgInfo;
  setOrgInfo: (info: OrgInfo) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function StepOrgInfo({ orgInfo, setOrgInfo, onNext, onBack }: Props) {
  const valid = orgInfo.name.trim() && orgInfo.type && orgInfo.size_range;

  return (
    <div>
      <h2 className="font-display italic text-2xl text-warm-900">Tu organización</h2>
      <p className="mt-1.5 text-sm text-warm-500">
        Datos básicos para contextualizar el diagnóstico.
      </p>

      <div className="mt-7 space-y-5">
        {/* Org name */}
        <div>
          <label className="block text-sm font-medium text-warm-900 mb-1.5">
            Nombre de la organización
          </label>
          <input
            type="text"
            value={orgInfo.name}
            onChange={(e) => setOrgInfo({ ...orgInfo, name: e.target.value })}
            className="block w-full rounded-md border border-warm-300 bg-white px-3 py-2.5 text-sm text-warm-900 placeholder:text-warm-400 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="Mi empresa"
          />
        </div>

        {/* Org type */}
        <div>
          <label className="block text-sm font-medium text-warm-900 mb-2">
            Tipo
          </label>
          <div className="grid grid-cols-2 gap-2">
            {ORG_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setOrgInfo({ ...orgInfo, type: t.value })}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors text-left ${
                  orgInfo.type === t.value
                    ? "border-accent bg-accent/8 text-accent"
                    : "border-warm-200 bg-white text-warm-700 hover:border-warm-300 hover:bg-warm-50"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Size range */}
        <div>
          <label className="block text-sm font-medium text-warm-900 mb-2">
            Tamaño aproximado
          </label>
          <div className="grid grid-cols-2 gap-2">
            {SIZE_RANGES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => setOrgInfo({ ...orgInfo, size_range: s.value })}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors text-left ${
                  orgInfo.size_range === s.value
                    ? "border-accent bg-accent/8 text-accent"
                    : "border-warm-200 bg-white text-warm-700 hover:border-warm-300 hover:bg-warm-50"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1 text-sm font-medium text-warm-500 hover:text-warm-900 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Atrás
        </button>
        <button
          onClick={onNext}
          disabled={!valid}
          className="inline-flex items-center gap-2 rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-40 transition-colors"
        >
          Siguiente
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
