"use client";

import { useState } from "react";
import { Plus, LayoutTemplate, FileSpreadsheet } from "lucide-react";
import TemplateOverlay from "./TemplateOverlay";
import CsvImportPanel from "./CsvImportPanel";

interface EmptyStateProps {
  orgId: string;
  onCreateNode: () => void;
  onTemplateApplied: () => void;
  onCsvImported: () => void;
}

export default function EmptyState({
  orgId,
  onCreateNode,
  onTemplateApplied,
  onCsvImported,
}: EmptyStateProps) {
  const [showTemplates, setShowTemplates] = useState(false);
  const [showCsv, setShowCsv] = useState(false);

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

        <h2 className="text-xl font-bold text-gray-900">
          Construye tu organización
        </h2>
        <p className="mt-2 text-sm text-gray-500 max-w-xs mx-auto">
          Crea la estructura de tu organización visualmente. Agrega nodos,
          conéctalos y define roles y áreas.
        </p>

        {/* 3 CTAs */}
        <div className="mt-8 space-y-3">
          <button
            onClick={onCreateNode}
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
