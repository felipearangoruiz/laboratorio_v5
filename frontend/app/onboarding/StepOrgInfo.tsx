"use client";

interface OrgData {
  org_name: string;
  org_type: string;
  size_range: string;
}

interface Props {
  data: OrgData;
  onChange: (data: OrgData) => void;
  onNext: () => void;
  onBack: () => void;
}

const ORG_TYPES = [
  { value: "empresa", label: "Empresa" },
  { value: "ong", label: "ONG / Fundación" },
  { value: "equipo", label: "Equipo / Área" },
  { value: "otro", label: "Otro" },
];

const SIZE_RANGES = [
  { value: "1-10", label: "1 a 10 personas" },
  { value: "11-50", label: "11 a 50 personas" },
  { value: "51-200", label: "51 a 200 personas" },
  { value: "200+", label: "Más de 200 personas" },
];

export default function StepOrgInfo({ data, onChange, onNext, onBack }: Props) {
  const canContinue = data.org_name.trim().length > 0;

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900">
        Cuéntanos de tu organización
      </h2>
      <p className="mt-2 text-sm text-gray-500">
        Esta información nos ayuda a contextualizar el diagnóstico.
      </p>

      <div className="mt-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Nombre de la organización
          </label>
          <input
            type="text"
            value={data.org_name}
            onChange={(e) => onChange({ ...data, org_name: e.target.value })}
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
            placeholder="Mi Organización"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Tipo de organización
          </label>
          <select
            value={data.org_type}
            onChange={(e) => onChange({ ...data, org_type: e.target.value })}
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none bg-white"
          >
            {ORG_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Tamaño
          </label>
          <select
            value={data.size_range}
            onChange={(e) => onChange({ ...data, size_range: e.target.value })}
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none bg-white"
          >
            {SIZE_RANGES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-8 flex gap-3">
        <button
          onClick={onBack}
          className="px-4 py-2.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Atrás
        </button>
        <button
          onClick={onNext}
          disabled={!canContinue}
          className="flex-1 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
        >
          Continuar
        </button>
      </div>
    </div>
  );
}
