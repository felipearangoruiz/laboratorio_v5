"use client";

// ============================================================
// Sprint 2.B — PersonPanel
// ============================================================
// Panel contextual de capa Estructura para nodos type='person'.
// Reemplaza a SidePanel+CollectionPanel legacy. Consume Node +
// NodeState del modelo nuevo; todas las ediciones van al compat
// layer (updateGroup) o al endpoint nativo (updateNode para
// attrs.admin_notes).

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Mail, X } from "lucide-react";
import {
  updateGroup,
  updateNode,
  inviteFromNode,
  revokeInvitation,
  ApiError,
} from "@/lib/api";
import { mapNodeStateToLegacyStatus } from "@/lib/view-models/legacyOrgNodeAdapter";
import type { Node as ModelNode, NodeState } from "@/lib/types";
import NodeFilesSection from "./NodeFilesSection";

interface PersonPanelProps {
  node: ModelNode;
  nodeState: NodeState | undefined;
  orgId: string;
  onClose: () => void;
  onDelete?: (nodeId: string) => void | Promise<void>;
  onRefetch: () => void | Promise<void>;
}

type SaveState = "idle" | "saving" | "saved" | "error";

const inputCls =
  "w-full rounded-md border border-warm-300 bg-white px-3 py-2 text-sm text-warm-900 placeholder:text-warm-400 focus:border-accent focus:ring-1 focus:ring-accent outline-none";

function SaveIndicator({ state }: { state: SaveState }) {
  if (state === "idle") return null;
  if (state === "saving")
    return <Loader2 className="w-3 h-3 animate-spin text-warm-400" />;
  if (state === "saved")
    return <span className="text-[11px] text-emerald-500">Guardado</span>;
  return <span className="text-[11px] text-rose-500">Error al guardar</span>;
}

function StatusBadge({
  status,
}: {
  status: "none" | "pending" | "in_progress" | "completed" | "expired";
}) {
  const map = {
    none: { label: "Sin invitar", cls: "bg-warm-100 text-warm-600" },
    pending: { label: "Invitado", cls: "bg-warm-100 text-warm-600" },
    in_progress: { label: "En progreso", cls: "bg-amber-100 text-amber-700" },
    completed: { label: "Completado", cls: "bg-emerald-100 text-emerald-700" },
    expired: {
      label: "Expirado",
      cls: "bg-warm-100 text-warm-500 border border-dashed border-warm-300",
    },
  };
  const { label, cls } = map[status];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${cls}`}>
      {label}
    </span>
  );
}

export default function PersonPanel({
  node,
  nodeState,
  orgId,
  onClose,
  onDelete,
  onRefetch,
}: PersonPanelProps) {
  const attrs = (node.attrs ?? {}) as Record<string, unknown>;
  const initialName = node.name;
  const initialRole = (attrs.tarea_general as string) ?? "";
  const initialEmail = (attrs.email as string) ?? "";
  const initialNotes = (attrs.admin_notes as string) ?? "";
  const interviewToken = (attrs.interview_token as string) ?? "";

  const [name, setName] = useState(initialName);
  const [role, setRole] = useState(initialRole);
  const [email, setEmail] = useState(initialEmail);
  const [adminNotes, setAdminNotes] = useState(initialNotes);

  const [nameState, setNameState] = useState<SaveState>("idle");
  const [roleState, setRoleState] = useState<SaveState>("idle");
  const [emailState, setEmailState] = useState<SaveState>("idle");
  const [notesState, setNotesState] = useState<SaveState>("idle");

  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState(false);

  // Reset when switching nodes.
  useEffect(() => {
    setName(initialName);
    setRole(initialRole);
    setEmail(initialEmail);
    setAdminNotes(initialNotes);
    setNameState("idle");
    setRoleState("idle");
    setEmailState("idle");
    setNotesState("idle");
    setInviteError(null);
    setConfirmRevoke(false);
  }, [node.id, initialName, initialRole, initialEmail, initialNotes]);

  // ── Debounced autosave helpers ──────────────────────────────
  const savedRef = useRef({
    name: initialName,
    role: initialRole,
    email: initialEmail,
    adminNotes: initialNotes,
  });

  useEffect(() => {
    savedRef.current = {
      name: initialName,
      role: initialRole,
      email: initialEmail,
      adminNotes: initialNotes,
    };
  }, [node.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const setSavedFlash = useCallback(
    (setter: (s: SaveState) => void) => {
      setter("saved");
      setTimeout(() => setter("idle"), 1500);
    },
    [],
  );

  // Name autosave
  useEffect(() => {
    if (name === savedRef.current.name) return;
    const t = setTimeout(async () => {
      setNameState("saving");
      try {
        await updateGroup(node.id, { name });
        savedRef.current.name = name;
        setSavedFlash(setNameState);
        await onRefetch();
      } catch {
        setNameState("error");
      }
    }, 1000);
    return () => clearTimeout(t);
  }, [name, node.id, onRefetch, setSavedFlash]);

  // Role autosave (→ attrs.tarea_general via compat layer)
  useEffect(() => {
    if (role === savedRef.current.role) return;
    const t = setTimeout(async () => {
      setRoleState("saving");
      try {
        await updateGroup(node.id, { tarea_general: role });
        savedRef.current.role = role;
        setSavedFlash(setRoleState);
        await onRefetch();
      } catch {
        setRoleState("error");
      }
    }, 1000);
    return () => clearTimeout(t);
  }, [role, node.id, onRefetch, setSavedFlash]);

  // Email autosave
  useEffect(() => {
    if (email === savedRef.current.email) return;
    const t = setTimeout(async () => {
      setEmailState("saving");
      try {
        await updateGroup(node.id, { email });
        savedRef.current.email = email;
        setSavedFlash(setEmailState);
        await onRefetch();
      } catch {
        setEmailState("error");
      }
    }, 1000);
    return () => clearTimeout(t);
  }, [email, node.id, onRefetch, setSavedFlash]);

  // admin_notes autosave — vía PATCH /nodes nativo.
  // Commit 0 del Turno A garantiza que el compat layer de /groups
  // preserva attrs.admin_notes (no lo pisa al re-serializar).
  useEffect(() => {
    if (adminNotes === savedRef.current.adminNotes) return;
    const t = setTimeout(async () => {
      setNotesState("saving");
      try {
        await updateNode(node.id, {
          attrs: { ...(node.attrs ?? {}), admin_notes: adminNotes },
        });
        savedRef.current.adminNotes = adminNotes;
        setSavedFlash(setNotesState);
        await onRefetch();
      } catch {
        setNotesState("error");
      }
    }, 1000);
    return () => clearTimeout(t);
  }, [adminNotes, node.id, node.attrs, onRefetch, setSavedFlash]);

  // ── Estado de invitación ─────────────────────────────────────
  // Estado preferido viene de NodeState (modelo nuevo). Fallback a
  // attrs.token_status para respondientes invitados vía endpoint legacy
  // que aún no crea NodeState. Deuda Sprint 2.C: migrar
  // /nodes/{id}/invite a nativo NodeState, lo cual permitirá eliminar
  // este fallback.
  const status = mapNodeStateToLegacyStatus(nodeState?.status, attrs.token_status);

  async function handleInvite() {
    if (!email) return;
    setInviting(true);
    setInviteError(null);
    try {
      await inviteFromNode(orgId, node.id, {
        name: node.name,
        role_label: role || "",
      });
      await onRefetch();
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "No se pudo enviar la invitación";
      setInviteError(msg);
    } finally {
      setInviting(false);
    }
  }

  async function handleCopyLink() {
    if (!interviewToken) return;
    const link = `${window.location.origin}/interview/${interviewToken}`;
    try {
      await navigator.clipboard.writeText(link);
    } catch {
      /* ignore */
    }
  }

  async function handleRevoke() {
    try {
      await revokeInvitation(node.id);
      await onRefetch();
      setConfirmRevoke(false);
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "No se pudo revocar";
      setInviteError(msg);
    }
  }

  return (
    <aside className="absolute right-0 top-0 h-full w-[420px] bg-white border-l border-warm-200 shadow-xl flex flex-col z-30">
      <header className="flex items-center justify-between px-5 py-4 border-b border-warm-200">
        <div className="flex-1 min-w-0">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-transparent text-lg font-semibold text-warm-900 outline-none focus:border-b focus:border-accent"
            placeholder="Nombre"
          />
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] uppercase tracking-wide text-warm-400">
              Persona
            </span>
            <SaveIndicator state={nameState} />
          </div>
        </div>
        <button
          onClick={onClose}
          className="ml-3 p-1 rounded hover:bg-warm-100 text-warm-500"
          aria-label="Cerrar"
        >
          <X className="w-4 h-4" />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
        {/* Info básica */}
        <section>
          <h3 className="text-xs uppercase tracking-wide text-warm-500 mb-2">
            Información
          </h3>
          <div className="space-y-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-warm-600">Rol</label>
                <SaveIndicator state={roleState} />
              </div>
              <input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className={inputCls}
                placeholder="Ej. Líder de equipo"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-warm-600">Correo</label>
                <SaveIndicator state={emailState} />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputCls}
                placeholder="persona@ejemplo.com"
              />
            </div>
          </div>
        </section>

        {/* Estado de respuesta */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs uppercase tracking-wide text-warm-500">
              Estado de respuesta
            </h3>
            <StatusBadge status={status} />
          </div>

          <div className="space-y-2">
            {status === "none" && !email && (
              <p className="text-xs text-warm-500">
                Agrega un correo para invitar a esta persona.
              </p>
            )}
            {status === "none" && email && (
              <button
                onClick={handleInvite}
                disabled={inviting}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-accent text-white text-sm hover:bg-accent-hover disabled:opacity-50"
              >
                <Mail className="w-4 h-4" />
                {inviting ? "Invitando…" : "Invitar"}
              </button>
            )}
            {(status === "pending" || status === "in_progress") && (
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={handleCopyLink}
                  disabled={!interviewToken}
                  className="px-3 py-2 rounded-md border border-warm-300 text-sm text-warm-700 hover:bg-warm-100 disabled:opacity-50"
                >
                  Copiar link
                </button>
                {!confirmRevoke ? (
                  <button
                    onClick={() => setConfirmRevoke(true)}
                    className="px-3 py-2 rounded-md border border-rose-300 text-sm text-rose-600 hover:bg-rose-50"
                  >
                    Revocar
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-warm-600">
                      ¿Seguro? Esto inutiliza el link.
                    </span>
                    <button
                      onClick={handleRevoke}
                      className="px-2 py-1 rounded bg-rose-600 text-white text-xs"
                    >
                      Sí, revocar
                    </button>
                    <button
                      onClick={() => setConfirmRevoke(false)}
                      className="px-2 py-1 rounded border border-warm-300 text-xs text-warm-600"
                    >
                      Cancelar
                    </button>
                  </div>
                )}
              </div>
            )}
            {(status === "completed" || status === "expired") && (
              <button
                disabled
                title="Visor de respuestas (pendiente Turno C)"
                className="px-3 py-2 rounded-md border border-warm-300 text-sm text-warm-500 opacity-60 cursor-not-allowed"
              >
                Ver respuestas
              </button>
            )}
            {inviteError && (
              <p className="text-xs text-rose-600">{inviteError}</p>
            )}
          </div>
        </section>

        {/* Archivos del nodo */}
        <NodeFilesSection nodeId={node.id} orgId={orgId} />

        {/* Notas del admin */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs uppercase tracking-wide text-warm-500">
              Notas del admin
            </h3>
            <SaveIndicator state={notesState} />
          </div>
          <textarea
            value={adminNotes}
            onChange={(e) => setAdminNotes(e.target.value)}
            rows={6}
            className={`${inputCls} resize-y`}
            placeholder="Notas privadas visibles solo para el admin."
          />
        </section>

        {onDelete && (
          <section className="pt-4 border-t border-warm-200">
            <button
              onClick={() => onDelete(node.id)}
              className="text-xs text-rose-600 hover:underline"
            >
              Eliminar nodo
            </button>
          </section>
        )}
      </div>
    </aside>
  );
}
