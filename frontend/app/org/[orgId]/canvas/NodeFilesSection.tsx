"use client";

// ============================================================
// Sprint 2.B Commit 6b — NodeFilesSection
// ============================================================
// Sección compacta de archivos por nodo, integrada en los
// paneles contextuales (PersonPanel, UnitPanel). Consume los
// endpoints /nodes/{node_id}/documents creados en el Commit 6a.

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  FileText,
  Loader2,
  Trash2,
  Upload,
} from "lucide-react";
import {
  ApiError,
  deleteNodeDocument,
  listNodeDocuments,
  uploadNodeDocument,
  type NodeDocument,
} from "@/lib/api";

interface NodeFilesSectionProps {
  nodeId: string;
  orgId: string;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function NodeFilesSection({ nodeId }: NodeFilesSectionProps) {
  const [docs, setDocs] = useState<NodeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadLabel, setUploadLabel] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadDocs() {
    try {
      const data = await listNodeDocuments(nodeId);
      setDocs(data);
    } catch {
      /* ignore */
    }
    setLoading(false);
  }

  useEffect(() => {
    setLoading(true);
    loadDocs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeId]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    if (file && !uploadLabel) {
      setUploadLabel(file.name.replace(/\.[^/.]+$/, ""));
    }
  }

  async function handleUpload() {
    if (!selectedFile || !uploadLabel.trim()) return;
    setUploading(true);
    setError("");
    try {
      await uploadNodeDocument(
        nodeId,
        selectedFile,
        uploadLabel.trim(),
        "other",
      );
      setSelectedFile(null);
      setUploadLabel("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadDocs();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Error al subir el archivo");
    }
    setUploading(false);
  }

  async function handleDelete(docId: string) {
    if (
      typeof window !== "undefined" &&
      !window.confirm("¿Eliminar este archivo?")
    ) {
      return;
    }
    setDeletingId(docId);
    try {
      await deleteNodeDocument(nodeId, docId);
      await loadDocs();
    } catch {
      /* ignore */
    }
    setDeletingId(null);
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs uppercase tracking-wide text-warm-500">
          Archivos ({docs.length})
        </h3>
      </div>

      {/* Upload */}
      <div className="space-y-2 mb-3">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt"
          onChange={handleFileChange}
          className="hidden"
          id={`node-file-input-${nodeId}`}
        />
        <label
          htmlFor={`node-file-input-${nodeId}`}
          className="flex items-center gap-2 w-full rounded-md border border-dashed border-warm-300 bg-warm-50 px-3 py-2 cursor-pointer hover:border-accent hover:bg-accent/5 transition-colors"
        >
          <Upload className="w-3.5 h-3.5 text-warm-400 flex-shrink-0" />
          <span className="text-xs text-warm-500 truncate">
            {selectedFile ? selectedFile.name : "Seleccionar PDF, DOCX o TXT"}
          </span>
        </label>

        {selectedFile && (
          <>
            <input
              type="text"
              value={uploadLabel}
              onChange={(e) => setUploadLabel(e.target.value)}
              placeholder="Nombre del archivo"
              className="w-full rounded-md border border-warm-300 bg-white px-3 py-1.5 text-xs text-warm-900 placeholder:text-warm-400 focus:border-accent focus:ring-1 focus:ring-accent outline-none"
            />
            <button
              onClick={handleUpload}
              disabled={uploading || !uploadLabel.trim()}
              className="w-full py-1.5 bg-accent text-white text-xs font-semibold rounded-md hover:bg-accent-hover disabled:opacity-50 flex items-center justify-center gap-1.5 transition-colors"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" /> Subiendo…
                </>
              ) : (
                <>
                  <Upload className="w-3 h-3" /> Subir
                </>
              )}
            </button>
          </>
        )}

        {error && (
          <div className="flex items-start gap-1.5 rounded-md bg-red-50 border border-red-200 px-2 py-1.5">
            <AlertCircle className="w-3 h-3 text-red-600 flex-shrink-0 mt-0.5" />
            <span className="text-[11px] text-red-700">{error}</span>
          </div>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-4 h-4 animate-spin text-warm-400" />
        </div>
      ) : docs.length === 0 ? (
        <div className="text-xs text-warm-400 italic">
          Sin archivos en este nodo.
        </div>
      ) : (
        <ul className="space-y-1.5">
          {docs.map((doc) => (
            <li
              key={doc.id}
              className="flex items-start gap-2 rounded-md border border-warm-200 bg-white px-2.5 py-2"
            >
              <FileText
                className="w-3.5 h-3.5 text-accent flex-shrink-0 mt-0.5"
                strokeWidth={1.5}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-warm-900 truncate">
                  {doc.label}
                </p>
                <p className="text-[10px] text-warm-400 truncate">
                  {doc.filename}
                </p>
                <p className="text-[10px] text-warm-400">
                  {formatDate(doc.created_at)}
                </p>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                disabled={deletingId === doc.id}
                className="text-warm-300 hover:text-red-500 flex-shrink-0 transition-colors disabled:opacity-50"
                title="Eliminar archivo"
              >
                {deletingId === doc.id ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Trash2 className="w-3 h-3" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
