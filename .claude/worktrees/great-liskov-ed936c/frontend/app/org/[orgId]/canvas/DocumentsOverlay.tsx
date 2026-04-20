"use client";

import { useEffect, useRef, useState } from "react";
import { X, Upload, Trash2, FileText, Loader2, AlertCircle } from "lucide-react";
import { getDocuments, uploadDocument, deleteDocument, ApiError } from "@/lib/api";

interface DocItem {
  id: string;
  organization_id: string;
  label: string;
  doc_type: string;
  filename: string;
  created_at: string;
}

interface Props {
  orgId: string;
  onClose: () => void;
}

const DOC_TYPE_LABELS: Record<string, string> = {
  institutional: "Institucional",
  other: "Otro",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function DocumentsOverlay({ orgId, onClose }: Props) {
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadLabel, setUploadLabel] = useState("");
  const [uploadDocType, setUploadDocType] = useState("institutional");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadDocs() {
    try {
      const data = await getDocuments(orgId);
      setDocs(data);
    } catch { /* ignore */ }
    setLoading(false);
  }

  useEffect(() => {
    loadDocs();
  }, [orgId]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    if (file && !uploadLabel) {
      // Pre-fill label with filename (without extension)
      setUploadLabel(file.name.replace(/\.[^/.]+$/, ""));
    }
  }

  async function handleUpload() {
    if (!selectedFile || !uploadLabel.trim()) return;
    setUploading(true);
    setError("");
    try {
      const doc = await uploadDocument(orgId, selectedFile, uploadLabel.trim(), uploadDocType);
      setDocs((prev) => [doc, ...prev]);
      setSelectedFile(null);
      setUploadLabel("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Error al subir el documento");
    }
    setUploading(false);
  }

  async function handleDelete(docId: string) {
    setDeletingId(docId);
    try {
      await deleteDocument(orgId, docId);
      setDocs((prev) => prev.filter((d) => d.id !== docId));
    } catch { /* ignore */ }
    setDeletingId(null);
  }

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Dim canvas */}
      <div className="flex-1" style={{ background: "rgba(0,0,0,0.45)" }} />

      {/* Panel */}
      <div className="w-96 h-full bg-warm-50 border-l border-warm-200 shadow-warm-md flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-warm-200 bg-white">
          <div>
            <h2 className="font-display italic text-lg text-warm-900">Documentos institucionales</h2>
            <p className="text-xs text-warm-500 mt-0.5">Estatutos, misión, manuales y más</p>
          </div>
          <button onClick={onClose} className="text-warm-400 hover:text-warm-700 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Upload area */}
        <div className="px-5 py-4 border-b border-warm-200 bg-white space-y-3">
          {/* File input */}
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt"
              onChange={handleFileChange}
              className="hidden"
              id="doc-file-input"
            />
            <label
              htmlFor="doc-file-input"
              className="flex items-center gap-2 w-full rounded-md border border-dashed border-warm-300 bg-warm-50 px-3 py-2.5 cursor-pointer hover:border-accent hover:bg-accent/5 transition-colors"
            >
              <Upload className="w-4 h-4 text-warm-400 flex-shrink-0" />
              <span className="text-sm text-warm-500 truncate">
                {selectedFile ? selectedFile.name : "Seleccionar PDF, DOCX o TXT"}
              </span>
            </label>
          </div>

          {selectedFile && (
            <>
              <input
                type="text"
                value={uploadLabel}
                onChange={(e) => setUploadLabel(e.target.value)}
                placeholder="Nombre del documento"
                className="w-full rounded-md border border-warm-300 bg-white px-3 py-2 text-sm text-warm-900 placeholder:text-warm-400 focus:border-accent focus:ring-1 focus:ring-accent outline-none"
              />
              <select
                value={uploadDocType}
                onChange={(e) => setUploadDocType(e.target.value)}
                className="w-full rounded-md border border-warm-300 bg-white px-3 py-2 text-sm text-warm-900 focus:border-accent focus:ring-1 focus:ring-accent outline-none"
              >
                <option value="institutional">Institucional</option>
                <option value="other">Otro</option>
              </select>
              <button
                onClick={handleUpload}
                disabled={uploading || !uploadLabel.trim()}
                className="w-full py-2.5 bg-accent text-white text-sm font-semibold rounded-md hover:bg-accent-hover disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
              >
                {uploading ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Subiendo…</>
                ) : (
                  <><Upload className="w-4 h-4" /> Subir documento</>
                )}
              </button>
            </>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-md bg-red-50 border border-red-200 px-3 py-2">
              <AlertCircle className="w-3.5 h-3.5 text-red-600 flex-shrink-0 mt-0.5" />
              <span className="text-xs text-red-700">{error}</span>
            </div>
          )}
        </div>

        {/* Document list */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-5 h-5 animate-spin text-warm-400" />
            </div>
          ) : docs.length === 0 ? (
            <div className="text-center py-10">
              <FileText className="w-8 h-8 text-warm-300 mx-auto mb-3" strokeWidth={1} />
              <p className="text-sm text-warm-500 font-medium">Sin documentos</p>
              <p className="text-xs text-warm-400 mt-1 leading-relaxed max-w-[220px] mx-auto">
                Sube estatutos, misión, manuales u otros documentos que ayuden al análisis
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {docs.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-start gap-3 rounded-md border border-warm-200 bg-white px-3 py-3"
                >
                  <FileText className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" strokeWidth={1.5} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-warm-900 truncate">{doc.label}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-warm-100 text-warm-500 font-medium">
                        {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
                      </span>
                      <span className="text-[10px] text-warm-400">{formatDate(doc.created_at)}</span>
                    </div>
                    <p className="text-[10px] text-warm-400 truncate mt-0.5">{doc.filename}</p>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="text-warm-300 hover:text-red-500 flex-shrink-0 transition-colors disabled:opacity-50"
                    title="Eliminar documento"
                  >
                    {deletingId === doc.id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
