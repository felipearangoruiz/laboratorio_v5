"use client";

import { useState } from "react";
import { X, Upload, ArrowRight } from "lucide-react";
import { importCsv, ApiError } from "@/lib/api";

interface Props {
  orgId: string;
  onImported: () => void;
  onClose: () => void;
}

interface CsvRow {
  name: string;
  role: string;
  area: string;
  boss: string;
}

type Step = "paste" | "preview" | "done";

export default function CsvImportPanel({ orgId, onImported, onClose }: Props) {
  const [step, setStep] = useState<Step>("paste");
  const [rawText, setRawText] = useState("");
  const [rows, setRows] = useState<CsvRow[]>([]);
  const [error, setError] = useState("");
  const [importing, setImporting] = useState(false);

  function parseCsv() {
    setError("");
    const lines = rawText.trim().split("\n").filter(Boolean);
    if (lines.length < 2) {
      setError("Necesitas al menos una fila de encabezado y una de datos");
      return;
    }

    const header = lines[0].split(/[,;\t]/).map((h) => h.trim().toLowerCase());
    const nameIdx = header.findIndex((h) =>
      ["nombre", "name"].includes(h)
    );
    const roleIdx = header.findIndex((h) =>
      ["cargo", "role", "puesto", "posicion", "position"].includes(h)
    );
    const areaIdx = header.findIndex((h) =>
      ["area", "departamento", "department"].includes(h)
    );
    const bossIdx = header.findIndex((h) =>
      ["jefe", "boss", "reporta", "jefe directo", "manager", "reporta a"].includes(h)
    );

    if (nameIdx === -1) {
      setError("No se encontró columna 'nombre' o 'name' en el encabezado");
      return;
    }

    const parsed: CsvRow[] = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(/[,;\t]/).map((c) => c.trim());
      const name = cols[nameIdx] || "";
      if (!name) continue;

      parsed.push({
        name,
        role: roleIdx >= 0 ? cols[roleIdx] || "" : "",
        area: areaIdx >= 0 ? cols[areaIdx] || "" : "",
        boss: bossIdx >= 0 ? cols[bossIdx] || "" : "",
      });
    }

    if (parsed.length === 0) {
      setError("No se encontraron datos válidos");
      return;
    }

    setRows(parsed);
    setStep("preview");
  }

  async function handleImport() {
    setImporting(true);
    setError("");
    try {
      await importCsv(orgId, rows);
      onImported();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Error al importar");
      setImporting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex justify-end">
      <div className="bg-white w-full max-w-md h-full shadow-xl flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-900">
            Importar estructura
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {error && (
            <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-lg">
              {error}
            </div>
          )}

          {step === "paste" && (
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600 mb-2">
                  Pega datos CSV con columnas: <strong>nombre</strong>, cargo,
                  area, jefe directo. Separados por coma, punto y coma o tab.
                </p>
                <p className="text-xs text-gray-400 mb-3">
                  Ejemplo: nombre,cargo,area,jefe directo
                </p>
              </div>
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                rows={12}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-xs font-mono focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
                placeholder={`nombre,cargo,area,jefe directo\nJuan García,CEO,Dirección,\nMaría López,CTO,Tecnología,Juan García\nCarlos Ruiz,Dev Lead,Tecnología,María López`}
              />
              <button
                onClick={parseCsv}
                disabled={!rawText.trim()}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
              >
                Previsualizar
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {step === "preview" && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Se importarán {rows.length} nodos:
              </p>
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium text-gray-600">Nombre</th>
                      <th className="text-left px-3 py-2 font-medium text-gray-600">Cargo</th>
                      <th className="text-left px-3 py-2 font-medium text-gray-600">Área</th>
                      <th className="text-left px-3 py-2 font-medium text-gray-600">Reporta a</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, i) => (
                      <tr key={i} className="border-t border-gray-100">
                        <td className="px-3 py-1.5 text-gray-900">{r.name}</td>
                        <td className="px-3 py-1.5 text-gray-600">{r.role}</td>
                        <td className="px-3 py-1.5 text-gray-600">{r.area}</td>
                        <td className="px-3 py-1.5 text-gray-600">{r.boss || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setStep("paste")}
                  className="flex-1 py-2.5 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50"
                >
                  Volver
                </button>
                <button
                  onClick={handleImport}
                  disabled={importing}
                  className="flex-1 inline-flex items-center justify-center gap-2 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
                >
                  <Upload className="w-4 h-4" />
                  {importing ? "Importando..." : "Importar"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
