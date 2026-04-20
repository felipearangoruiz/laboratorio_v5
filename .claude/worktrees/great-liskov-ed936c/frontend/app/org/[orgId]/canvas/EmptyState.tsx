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
  { type: "people", icon: User,   title: "Por personas", description: "Cada nodo es una persona con cargo" },
  { type: "areas",  icon: Users,  title: "Por áreas",    description: "Cada nodo es un departamento con miembros" },
  { type: "mixed",  icon: Layers, title: "Mixto",        description: "Combina personas y áreas" },
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
    <div className="h-full flex items-center justify-center" style={{ background: "#0D0D14" }}>
      <div className="text-center max-w-sm px-4">
        {/* Minimal org-tree illustration */}
        <div className="mx-auto mb-8 w-20 h-20 flex items-center justify-center">
          <svg viewBox="0 0 80 80" fill="none" className="w-full h-full opacity-30">
            <circle cx="40" cy="14" r="8" stroke="white" strokeWidth="1.5" />
            <circle cx="16" cy="58" r="7" stroke="white" strokeWidth="1.5" />
            <circle cx="64" cy="58" r="7" stroke="white" strokeWidth="1.5" />
            <line x1="40" y1="22" x2="16" y2="51" stroke="white" strokeWidth="1.5" />
            <line x1="40" y1="22" x2="64" y2="51" stroke="white" strokeWidth="1.5" />
          </svg>
        </div>

        {step === "choose" ? (
          <>
            <h2 className="font-display italic text-2xl text-white leading-tight">
              ¿Cómo está organizada tu empresa?
            </h2>
            <p className="mt-2 text-sm text-white/40 max-w-xs mx-auto">
              Elige la estructura que mejor represente tu organización.
            </p>

            <div className="mt-8 space-y-2">
              {STRUCTURE_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                return (
                  <button
                    key={opt.type}
                    onClick={() => handleTypeSelect(opt.type)}
                    disabled={saving}
                    className="w-full flex items-center gap-4 px-5 py-3.5 rounded-md border border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20 transition-colors text-left disabled:opacity-50"
                  >
                    <div className="w-9 h-9 rounded-md bg-white/8 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-4 h-4 text-white/60" strokeWidth={1.5} />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-white/80">{opt.title}</div>
                      <div className="text-xs text-white/35 mt-0.5">{opt.description}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </>
        ) : (
          <>
            <h2 className="font-display italic text-2xl text-white leading-tight">
              Construye tu organización
            </h2>
            <p className="mt-2 text-sm text-white/40 max-w-xs mx-auto">
              Agrega nodos, conéctalos y define la estructura.
            </p>

            <div className="mt-8 space-y-2">
              <button
                onClick={handleCreateNode}
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 bg-[#C2410C] text-white text-sm font-semibold rounded-md hover:bg-[#9A3412] transition-colors"
              >
                <Plus className="w-4 h-4" />
                Crear primer nodo
              </button>

              <button
                onClick={() => setShowTemplates(true)}
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 border border-white/20 text-white/70 text-sm font-medium rounded-md hover:bg-white/6 hover:text-white transition-colors"
              >
                <LayoutTemplate className="w-4 h-4" />
                Usar template
              </button>

              <button
                onClick={() => setShowCsv(true)}
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-2.5 text-white/35 text-sm hover:text-white/60 transition-colors"
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
          onApplied={() => { setShowTemplates(false); onTemplateApplied(); }}
          onClose={() => setShowTemplates(false)}
        />
      )}

      {showCsv && (
        <CsvImportPanel
          orgId={orgId}
          onImported={() => { setShowCsv(false); onCsvImported(); }}
          onClose={() => setShowCsv(false)}
        />
      )}
    </div>
  );
}
