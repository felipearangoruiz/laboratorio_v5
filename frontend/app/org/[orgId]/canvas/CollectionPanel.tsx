"use client";

import { useEffect, useState, useCallback } from "react";
import {
  X,
  Mail,
  Copy,
  Check,
  MessageCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  RefreshCw,
  Link2,
} from "lucide-react";
import { inviteFromNode, revokeInvitation, getNodeInterviews, ApiError } from "@/lib/api";

interface Props {
  orgId: string;
  nodeId: string;
  nodeName: string;
  nodeEmail: string;
  interviewStatus: string; // "none" | "pending" | "in_progress" | "completed" | "expired"
  onClose: () => void;
  onChanged: () => void;
  onSwitchToEstructura: () => void;
}

interface MemberDetail {
  member_id: string;
  interview_token: string;
  token_status: string;
  submitted_at: string | null;
  reminder_count: number;
}

function interviewUrl(token: string): string {
  if (typeof window === "undefined") return "";
  return `${window.location.origin}/interview/${token}`;
}

function whatsappUrl(nodeName: string, token: string): string {
  const url = interviewUrl(token);
  const text = `Hola, te invito a participar en un diagnóstico anónimo de nuestra organización (5-10 min). Responde aquí: ${url}`;
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function CollectionPanel({
  orgId,
  nodeId,
  nodeName,
  nodeEmail,
  interviewStatus,
  onClose,
  onChanged,
  onSwitchToEstructura,
}: Props) {
  const [member, setMember] = useState<MemberDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const loadMember = useCallback(async () => {
    if (interviewStatus === "none") return;
    setLoading(true);
    try {
      const list = await getNodeInterviews(orgId, nodeId);
      if (list.length > 0) {
        // Highest-priority member: completed > in_progress > pending > expired
        const priority: Record<string, number> = {
          completed: 4, in_progress: 3, pending: 2, expired: 1,
        };
        const sorted = [...list].sort(
          (a, b) => (priority[b.token_status] ?? 0) - (priority[a.token_status] ?? 0)
        );
        setMember(sorted[0]);
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [orgId, nodeId, interviewStatus]);

  useEffect(() => {
    setMember(null);
    setError("");
    loadMember();
  }, [loadMember]);

  async function handleGenerateLink() {
    setGenerating(true);
    setError("");
    try {
      const res = await inviteFromNode(orgId, nodeId, { name: nodeName });
      setMember({
        member_id: res.member_id,
        interview_token: res.token,
        token_status: res.status,
        submitted_at: null,
        reminder_count: 0,
      });
      onChanged();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("No se pudo generar el link");
    }
    setGenerating(false);
  }

  async function handleRevoke() {
    if (!member) return;
    setRevoking(true);
    try {
      await revokeInvitation(member.member_id);
      setMember({ ...member, token_status: "expired" });
      onChanged();
    } catch { /* ignore */ }
    setRevoking(false);
  }

  async function handleReenviar() {
    setGenerating(true);
    setError("");
    try {
      const res = await inviteFromNode(orgId, nodeId, { name: nodeName });
      setMember({
        member_id: res.member_id,
        interview_token: res.token,
        token_status: res.status,
        submitted_at: null,
        reminder_count: 0,
      });
      onChanged();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("No se pudo reenviar el link");
    }
    setGenerating(false);
  }

  function copyLink(token: string) {
    const url = interviewUrl(token);
    navigator.clipboard.writeText(url).catch(() => {
      const input = document.createElement("input");
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
    });
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // Determine active state
  const effectiveStatus = member?.token_status ?? interviewStatus;
  const hasEmail = nodeEmail && nodeEmail.trim() !== "";

  return (
    <div className="absolute top-0 right-0 h-full w-80 bg-warm-50 border-l border-warm-200 shadow-warm-md z-10 flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between px-5 py-4 border-b border-warm-200 bg-white">
        <div className="flex-1 min-w-0 pr-2">
          <h3 className="font-display italic text-lg text-warm-900 leading-tight truncate">
            {nodeName}
          </h3>
          <p className="text-xs text-warm-500 mt-0.5">Recolección</p>
        </div>
        <button onClick={onClose} className="text-warm-400 hover:text-warm-700 flex-shrink-0 mt-0.5">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-5">
        {error && (
          <div className="mb-4 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-4 h-4 animate-spin text-warm-400" />
          </div>
        ) : (
          <>
            {/* ── STATE A: No email ── */}
            {!hasEmail && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <div className="flex items-start gap-3 mb-3">
                  <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-amber-900">Sin email asignado</p>
                    <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                      Para invitar a un miembro, asigna un email en la capa Estructura.
                    </p>
                  </div>
                </div>
                <button
                  onClick={onSwitchToEstructura}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-800 hover:text-amber-900 transition-colors"
                >
                  <ArrowLeft className="w-3 h-3" />
                  Ir a Estructura
                </button>
              </div>
            )}

            {/* ── STATE B: Has email, not invited ── */}
            {hasEmail && (effectiveStatus === "none" || !member) && !generating && (
              <div className="space-y-4">
                <div className="rounded-md border border-warm-200 bg-white px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-warm-400 mb-1">
                    Email asignado
                  </p>
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-warm-400 flex-shrink-0" />
                    <span className="text-sm text-warm-700 truncate">{nodeEmail}</span>
                  </div>
                </div>

                <p className="text-xs text-warm-500 leading-relaxed">
                  Al generar el link, se crea un enlace único y anónimo para esta persona. Tú decides cómo compartirlo.
                </p>

                <button
                  onClick={handleGenerateLink}
                  disabled={generating}
                  className="w-full py-2.5 bg-accent text-white text-sm font-semibold rounded-md hover:bg-accent-hover disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
                >
                  <Link2 className="w-4 h-4" />
                  Generar link de entrevista
                </button>
              </div>
            )}

            {/* Generating spinner */}
            {generating && (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-4 h-4 animate-spin text-accent" />
              </div>
            )}

            {/* ── STATES C / E: Invited, In Progress, Expired ── */}
            {member && (effectiveStatus === "pending" || effectiveStatus === "in_progress" || effectiveStatus === "expired") && (
              <div className="space-y-4">
                {/* Status badge */}
                <div className="flex items-center gap-2">
                  {effectiveStatus === "pending" && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-xs font-semibold text-blue-700">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                      Invitado
                    </span>
                  )}
                  {effectiveStatus === "in_progress" && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-100 border border-blue-300 text-xs font-semibold text-blue-800">
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      En progreso
                    </span>
                  )}
                  {effectiveStatus === "expired" && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-orange-50 border border-orange-200 text-xs font-semibold text-orange-700">
                      <Clock className="w-3 h-3" />
                      Vencido
                    </span>
                  )}
                </div>

                {/* Email chip */}
                <div className="flex items-center gap-2 text-xs text-warm-500">
                  <Mail className="w-3 h-3 flex-shrink-0" />
                  <span className="truncate">{nodeEmail}</span>
                </div>

                {/* Link copy area */}
                <div className="rounded-md border border-warm-200 bg-white overflow-hidden">
                  <div className="px-3 py-2 bg-warm-50 border-b border-warm-200">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-warm-400">
                      Link de entrevista
                    </p>
                  </div>
                  <div className="px-3 py-2">
                    <p className="font-mono text-[10px] text-warm-500 break-all leading-relaxed">
                      {interviewUrl(member.interview_token)}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => copyLink(member.interview_token)}
                    className="flex-1 inline-flex items-center justify-center gap-1.5 py-2 rounded-md border border-warm-300 bg-white text-xs font-semibold text-warm-700 hover:bg-warm-50 transition-colors"
                  >
                    {copied ? (
                      <><Check className="w-3.5 h-3.5 text-green-600" /> Copiado</>
                    ) : (
                      <><Copy className="w-3.5 h-3.5" /> Copiar link</>
                    )}
                  </button>
                  <a
                    href={whatsappUrl(nodeName, member.interview_token)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 inline-flex items-center justify-center gap-1.5 py-2 rounded-md bg-green-600 text-xs font-semibold text-white hover:bg-green-700 transition-colors"
                  >
                    <MessageCircle className="w-3.5 h-3.5" />
                    WhatsApp
                  </a>
                </div>

                {/* Reenviar / Revocar */}
                <div className="flex gap-2 pt-1">
                  {effectiveStatus === "expired" && (
                    <button
                      onClick={handleReenviar}
                      disabled={generating}
                      className="flex-1 py-2 text-xs font-semibold rounded-md bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
                    >
                      Reenviar link
                    </button>
                  )}
                  {(effectiveStatus === "pending" || effectiveStatus === "in_progress") && (
                    <button
                      onClick={handleRevoke}
                      disabled={revoking}
                      className="text-xs text-red-500 hover:text-red-700 transition-colors disabled:opacity-50"
                    >
                      {revoking ? "Revocando…" : "Revocar"}
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* ── STATE D: Completed ── */}
            {member && effectiveStatus === "completed" && (
              <div className="space-y-4">
                <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                  <div className="flex items-center gap-3 mb-1">
                    <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
                    <p className="text-sm font-semibold text-green-900">Entrevista respondida</p>
                  </div>
                  {member.submitted_at && (
                    <p className="text-xs text-green-700 ml-8">
                      Respondió el {formatDate(member.submitted_at)}
                    </p>
                  )}
                </div>

                {/* Email chip */}
                <div className="flex items-center gap-2 text-xs text-warm-500">
                  <Mail className="w-3 h-3 flex-shrink-0" />
                  <span className="truncate">{nodeEmail}</span>
                </div>

                <button
                  disabled
                  className="w-full py-2.5 text-sm font-semibold rounded-md border border-warm-200 text-warm-400 cursor-not-allowed"
                >
                  Ver respuestas (próximamente)
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
