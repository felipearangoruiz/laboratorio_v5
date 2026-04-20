"use client";

import { useState } from "react";
import { getDiagnosisInput, ApiError } from "@/lib/api";
import { Sparkles, Loader2, AlertCircle } from "lucide-react";

interface Props {
  orgId: string;
  onDiagnosisGenerated: () => void;
}

export default function AnalysisLayer({ orgId, onDiagnosisGenerated }: Props) {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate() {
    setGenerating(true);
    setError("");
    try {
      // Fetch input bundle — verifies auth and data availability.
      // The actual analysis runs in the external Codex processor, which
      // calls GET /diagnosis/input and then POST /diagnosis when done.
      await getDiagnosisInput(orgId);
      // Nothing more to do here: poll loadMeta() until status === 'ready'
      onDiagnosisGenerated();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Error al preparar los datos para el diagnóstico.");
      }
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="absolute inset-0 flex items-center justify-center bg-gray-50/80 backdrop-blur-sm z-5">
      <div className="text-center max-w-md px-4">
        <div className="w-16 h-16 bg-gray-900 rounded-2xl flex items-center justify-center mx-auto mb-5">
          {generating ? (
            <Loader2 className="w-7 h-7 text-white animate-spin" />
          ) : (
            <Sparkles className="w-7 h-7 text-white" />
          )}
        </div>

        <h2 className="text-xl font-bold text-gray-900">
          {generating ? "Generando diagnóstico..." : "Analiza tu organización"}
        </h2>

        <p className="mt-2 text-sm text-gray-500 max-w-sm mx-auto">
          {generating
            ? "Preparando los datos para el procesador externo…"
            : "Has alcanzado el umbral de recolección. El diagnóstico se procesa externamente — cuando esté listo aparecerá aquí automáticamente."}
        </p>

        {error && (
          <div className="mt-4 p-3 bg-red-50 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-red-700 text-left">{error}</p>
          </div>
        )}

        {!generating && (
          <button
            onClick={handleGenerate}
            className="mt-6 inline-flex items-center gap-2 px-6 py-3 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800"
          >
            <Sparkles className="w-4 h-4" />
            Verificar datos
          </button>
        )}

        {generating && (
          <div className="mt-6">
            <div className="w-48 h-1.5 bg-gray-200 rounded-full mx-auto overflow-hidden">
              <div className="h-full bg-gray-900 rounded-full animate-pulse" style={{ width: "60%" }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
