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
  { value: "1-10", label: "1-10 personas" },
  { value: "11-50", label: "11-50 personas" },
  { value: "51-200", label: "51-200 personas" },
  { value: "200+", label: "Más de 200 personas" },
];

interface Props {
  orgInfo: OrgInfo;
  setOrgInfo: (info: OrgInfo) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function StepOrgInfo({
  orgInfo,
  setOrgInfo,
  onNext,
  onBack,
}: Props) {
  const valid = orgInfo.name.trim() && orgInfo.type && orgInfo.size_range;

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900">Tu organización</h2>
      <p className="mt-1 text-sm text-gray-500">
        Datos básicos para contextualizar el diagnóstico.
      </p>

      <div className="mt-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Nombre de la organización
          </label>
          <input
            type="text"
            value={orgInfo.name}
            onChange={(e) => setOrgInfo({ ...orgInfo, name: e.target.value })}
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
            placeholder="Mi empresa"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Tipo
          </label>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {ORG_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setOrgInfo({ ...orgInfo, type: t.value })}
                className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
                  orgInfo.type === t.value
                    ? "border-brand-600 bg-brand-50 text-brand-700 font-medium"
                    : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Tamaño aproximado
          </label>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {SIZE_RANGES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() =>
                  setOrgInfo({ ...orgInfo, size_range: s.value })
                }
                className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
                  orgInfo.size_range === s.value
                    ? "border-brand-600 bg-brand-50 text-brand-700 font-medium"
                    : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
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
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Atrás
        </button>
        <button
          onClick={onNext}
          disabled={!valid}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40 transition-colors"
        >
          Siguiente
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
