"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { getTemplates, applyTemplate, ApiError } from "@/lib/api";

interface Props {
  orgId: string;
  onApplied: () => void;
  onClose: () => void;
}

interface Template {
  id: string;
  name: string;
  description: string;
}

const TEMPLATE_PREVIEWS: Record<string, string[]> = {
  startup: ["CEO", "CTO", "COO", "Head Comercial", "Dev Lead", "Ventas"],
  ong: ["Director(a)", "Programas", "Admin", "Comunicaciones"],
  empresa_departamentos: ["Gerente General", "Finanzas", "Comercial", "Operaciones", "RRHH"],
  equipo_proyecto: ["Líder", "Analista", "Desarrollador", "QA", "Diseñador"],
};

export default function TemplateOverlay({ orgId, onApplied, onClose }: Props) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getTemplates(orgId)
      .then(setTemplates)
      .catch(() => setError("Error cargando templates"))
      .finally(() => setLoading(false));
  }, [orgId]);

  async function handleApply(templateId: string) {
    setApplying(templateId);
    setError("");
    try {
      await applyTemplate(orgId, templateId);
      onApplied();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Error aplicando template");
      setApplying(null);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">
            Elegir template
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto">
          {error && (
            <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-lg">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center py-8 text-sm text-gray-500">
              Cargando templates...
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {templates.map((t) => (
                <button
                  key={t.id}
                  onClick={() => handleApply(t.id)}
                  disabled={applying !== null}
                  className="text-left p-4 border border-gray-200 rounded-xl hover:border-gray-400 hover:shadow-sm transition-all disabled:opacity-50"
                >
                  {/* Mini preview */}
                  <div className="mb-3 p-3 bg-gray-50 rounded-lg">
                    <div className="flex flex-wrap gap-1">
                      {(TEMPLATE_PREVIEWS[t.id] || []).map((label, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 bg-white border border-gray-200 rounded text-[10px] text-gray-600"
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900">
                    {t.name}
                  </h3>
                  <p className="mt-1 text-xs text-gray-500">{t.description}</p>
                  {applying === t.id && (
                    <p className="mt-2 text-xs text-blue-600">Aplicando...</p>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
