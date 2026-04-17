"use client";

import { useEffect, useState } from "react";
import { X, Send, Bell, XCircle, Copy, Check, ExternalLink } from "lucide-react";
import {
  getNodeInterviews,
  inviteFromNode,
  sendReminder,
  revokeInvitation,
  ApiError,
} from "@/lib/api";

interface Props {
  orgId: string;
  nodeId: string;
  nodeName: string;
  onClose: () => void;
  onChanged: () => void;
}

interface MemberInterview {
  member_id: string;
  name: string;
  role_label: string;
  interview_token: string;
  token_status: string;
  submitted_at: string | null;
  reminder_count: number;
}

export default function CollectionPanel({
  orgId,
  nodeId,
  nodeName,
  onClose,
  onChanged,
}: Props) {
  const [members, setMembers] = useState<MemberInterview[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("");
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [error, setError] = useState("");
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  async function loadMembers() {
    try {
      const data = await getNodeInterviews(orgId, nodeId);
      setMembers(data);
    } catch {
      setError("Error cargando miembros");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMembers();
  }, [orgId, nodeId]);

  async function handleInvite() {
    if (!inviteName.trim() || !inviteEmail.trim()) return;
    setError("");
    try {
      await inviteFromNode(orgId, nodeId, {
        email: inviteEmail,
        name: inviteName,
        role_label: inviteRole,
      });
      setInviteName("");
      setInviteEmail("");
      setInviteRole("");
      setShowInviteForm(false);
      await loadMembers();
      onChanged();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
    }
  }

  async function handleRemind(memberId: string) {
    try {
      await sendReminder(memberId);
      await loadMembers();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
    }
  }

  async function handleRevoke(memberId: string) {
    try {
      await revokeInvitation(memberId);
      await loadMembers();
      onChanged();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
    }
  }

  function copyLink(token: string) {
    const url = `${window.location.origin}/interview/${token}`;
    navigator.clipboard.writeText(url);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  }

  const statusLabel: Record<string, { text: string; color: string }> = {
    pending: { text: "Invitado", color: "text-blue-600 bg-blue-50" },
    in_progress: { text: "En progreso", color: "text-blue-700 bg-blue-100" },
    completed: { text: "Completada", color: "text-emerald-700 bg-emerald-50" },
    expired: { text: "Vencida", color: "text-orange-700 bg-orange-50" },
  };

  return (
    <div className="absolute top-0 right-0 h-full w-80 bg-white border-l border-gray-200 shadow-lg z-10 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">{nodeName}</h3>
          <p className="text-xs text-gray-500">Recolección</p>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {error && (
          <div className="p-2 text-xs text-red-700 bg-red-50 rounded-lg">{error}</div>
        )}

        {loading ? (
          <p className="text-sm text-gray-400">Cargando...</p>
        ) : (
          <>
            {members.length === 0 && !showInviteForm && (
              <p className="text-sm text-gray-500 text-center py-4">
                No hay miembros invitados en este nodo.
              </p>
            )}

            {members.map((m) => {
              const st = statusLabel[m.token_status] || statusLabel.pending;
              return (
                <div key={m.member_id} className="p-3 bg-gray-50 rounded-lg space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{m.name}</p>
                      {m.role_label && (
                        <p className="text-xs text-gray-500">{m.role_label}</p>
                      )}
                    </div>
                    <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${st.color}`}>
                      {st.text}
                    </span>
                  </div>

                  <div className="flex gap-1.5">
                    {m.token_status !== "completed" && m.token_status !== "expired" && (
                      <>
                        <button
                          onClick={() => copyLink(m.interview_token)}
                          className="flex items-center gap-1 px-2 py-1 text-[10px] border border-gray-200 rounded hover:bg-white"
                        >
                          {copiedToken === m.interview_token ? (
                            <><Check className="w-3 h-3 text-emerald-500" /> Copiado</>
                          ) : (
                            <><Copy className="w-3 h-3" /> Enlace</>
                          )}
                        </button>
                        <button
                          onClick={() => handleRemind(m.member_id)}
                          disabled={m.reminder_count >= 3}
                          className="flex items-center gap-1 px-2 py-1 text-[10px] border border-gray-200 rounded hover:bg-white disabled:opacity-40"
                          title={m.reminder_count >= 3 ? "Máximo 3 recordatorios" : "Enviar recordatorio"}
                        >
                          <Bell className="w-3 h-3" /> ({m.reminder_count}/3)
                        </button>
                        <button
                          onClick={() => handleRevoke(m.member_id)}
                          className="flex items-center gap-1 px-2 py-1 text-[10px] text-red-600 border border-red-200 rounded hover:bg-red-50"
                        >
                          <XCircle className="w-3 h-3" /> Revocar
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}

            {showInviteForm && (
              <div className="p-3 border border-gray-200 rounded-lg space-y-2">
                <input
                  type="text"
                  placeholder="Nombre"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg outline-none focus:border-gray-900"
                />
                <input
                  type="email"
                  placeholder="Email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg outline-none focus:border-gray-900"
                />
                <input
                  type="text"
                  placeholder="Rol (opcional)"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-lg outline-none focus:border-gray-900"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowInviteForm(false)}
                    className="flex-1 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleInvite}
                    disabled={!inviteName.trim() || !inviteEmail.trim()}
                    className="flex-1 py-1.5 text-xs bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
                  >
                    Invitar
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="px-4 py-3 border-t border-gray-100">
        {!showInviteForm && (
          <button
            onClick={() => setShowInviteForm(true)}
            className="w-full inline-flex items-center justify-center gap-1.5 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800"
          >
            <Send className="w-3.5 h-3.5" />
            Invitar miembro
          </button>
        )}
      </div>
    </div>
  );
}
