"use client";

import { useState } from "react";
import { Plus, LayoutTemplate, FileSpreadsheet, User, Users, Layers } from "lucide-react";
import TemplateOverlay from "./TemplateOverlay";
import CsvImportPanel from "./CsvImportPanel";

type StructureType = "people" | "areas" | "mixed";

interface EmptyStateProps {
  orgId: string;
  onStructureTypeSelected: (type: StructureType) => Promise<void>;
  onCreateNode: (nodeType: "person" | "area") => void;
  onTemplateApplied: () => void;
  onCsvImported: () => void;
}

const STRUCTURE_OPTIONS: {
  type: StructureType;
  icon: typeof User;
  title: string;
  description: string;
}[] = [
  {
    type: "people",
    icon: User,
    title: "Por personas",
    description: "Cada nodo es una persona con cargo",
  },
  {
    type: "areas",
    icon: Users,
    title: "Por áreas",
    description: "Cada nodo es un departamento con miembros",
  },
  {
    type: "mixed",
    icon: Layers,
    title: "Mixto",
    description: "Combina personas y áreas",
  },
];

export default function EmptyState({
  orgId,
  onStructureTypeSelected,
  onCreateNode,
  onTemplateApplied,
  onCsvImported,
}: EmptyStateProps) {
  const [step, setStep] = useState<"choose" | "actions">("choose");
  const [selectedType, setSelectedType] = useState<StructureType | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showCsv, setShowCsv] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handleTypeSelect(type: StructureType) {
    setSelectedType(type);
    setSaving(true);
    await onStructureTypeSelected(type);
    setSaving(false);
    setStep("actions");
  }

  function handleCreateNode() {
    if (!selectedType) return;
    const nodeType = selectedType === "areas" ? "area" : "person";
    onCreateNode(nodeType);
  }

  return (
    <div className="h-full flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md px-4">
        {/* Illustration */}
        <div className="w-24 h-24 mx-auto mb-6 bg-gray-100 rounded-3xl flex items-center justify-center">
          <svg
            className="w-12 h-12 text-gray-400"
            fill="none"
            viewBox="0 0 48 48"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <circle cx="24" cy="12" r="6" />
            <circle cx="10" cy="36" r="5" />
            <circle cx="38" cy="36" r="5" />
            <line x1="24" y1="18" x2="10" y2="31" />
            <line x1="24" y1="18" x2="38" y2="31" />
          </svg>
        </div>

        {step === "choose" ? (
          <>
            <h2 className="text-xl font-bold text-gray-900">
              ¿Cómo está organizada tu empresa?
            </h2>
            <p className="mt-2 text-sm text-gray-500 max-w-xs mx-auto">
              Elige la estructura que mejor represente tu organización.
            </p>

            <div className="mt-8 space-y-3">
              {STRUCTURE_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                return (
                  <button
                    key={opt.type}
                    onClick={() => handleTypeSelect(opt.type)}
                    disabled={saving}
                    className="w-full flex items-center gap-4 px-5 py-4 border border-gray-200 rounded-xl hover:border-gray-400 hover:bg-gray-50 transition-colors text-left disabled:opacity-50"
                  >
                    <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-gray-600" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-900">
                        {opt.title}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {opt.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </>
        ) : (
          <>
            <h2 className="text-xl font-bold text-gray-900">
              Construye tu organización
            </h2>
            <p className="mt-2 text-sm text-gray-500 max-w-xs mx-auto">
              Agrega nodos, conéctalos y define la estructura.
            </p>

            <div className="mt-8 space-y-3">
              <button
                onClick={handleCreateNode}
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800"
              >
                <Plus className="w-4 h-4" />
                Crear primer nodo
              </button>

              <button
                onClick={() => setShowTemplates(true)}
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 border border-gray-300 text-gray-700 text-sm font-medium rounded-xl hover:bg-gray-50"
              >
                <LayoutTemplate className="w-4 h-4" />
                Usar template
              </button>

              <button
                onClick={() => setShowCsv(true)}
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-2.5 text-gray-500 text-sm hover:text-gray-700"
              >
                <FileSpreadsheet className="w-4 h-4" />
                Importar CSV
              </button>
            </div>
          </>
        )}
      </div>

      {showTemplates && (
        <TemplateOverlay
          orgId={orgId}
          onApplied={() => {
            setShowTemplates(false);
            onTemplateApplied();
          }}
          onClose={() => setShowTemplates(false)}
        />
      )}

      {showCsv && (
        <CsvImportPanel
          orgId={orgId}
          onImported={() => {
            setShowCsv(false);
            onCsvImported();
          }}
          onClose={() => setShowCsv(false)}
        />
      )}
    </div>
  );
}
