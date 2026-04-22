"use client";

/**
 * @deprecated — componente legacy pre-Sprint 2.B.
 * Reemplazado por UnitPanel/PersonPanel/NodeFilesSection en la capa
 * Estructura unificada (visión del Sprint 2.A).
 * Eliminación programada para Sprint 4 una vez confirmado cero consumidores.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { X, Trash2, Plus, UserMinus } from "lucide-react";

interface NodeMember {
  id: string;
  name: string;
  role_label: string;
  email: string;
}

interface SidePanelProps {
  nodeId: string;
  orgId: string;
  data: {
    label: string;
    area: string;
    role: string;
    email: string;
    level: number | null;
    nodeType: "person" | "area";
    contextNotes?: string | null;
  };
  onUpdate: (nodeId: string, data: Record<string, any>) => Promise<void>;
  onDelete: (nodeId: string) => Promise<void>;
  onClose: () => void;
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const inputCls =
  "w-full rounded-md border border-warm-300 bg-white px-3 py-2 text-sm text-warm-900 placeholder:text-warm-400 focus:border-accent focus:ring-1 focus:ring-accent outline-none";

export default function SidePanel({
  nodeId,
  orgId,
  data,
  onUpdate,
  onDelete,
  onClose,
}: SidePanelProps) {
  const isPerson = data.nodeType === "person";
  const [tab, setTab] = useState<"info" | "members">("info");

  // Info form state
  const [name, setName] = useState(data.label);
  const [role, setRole] = useState(data.role);
  const [email, setEmail] = useState(data.email || "");
  const [area, setArea] = useState(data.area);
  const [description, setDescription] = useState("");
  const [contextNotes, setContextNotes] = useState(data.contextNotes ?? "");
  const [savingContext, setSavingContext] = useState(false);
  const [savingEmail, setSavingEmail] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Track last-saved email to avoid unnecessary PATCHes
  const savedEmailRef = useRef(data.email || "");

  // Members state (for area nodes)
  const [members, setMembers] = useState<NodeMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [newMemberName, setNewMemberName] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("");
  const [addingMember, setAddingMember] = useState(false);

  useEffect(() => {
    setName(data.label);
    setRole(data.role);
    setEmail(data.email || "");
    savedEmailRef.current = data.email || "";
    setArea(data.area);
    setContextNotes(data.contextNotes ?? "");
    setConfirmDelete(false);
    setTab("info");
  }, [nodeId, data]);

  const loadMembers = useCallback(async () => {
    if (isPerson) return;
    setLoadingMembers(true);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API}/groups/${nodeId}/members`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const d = await res.json();
        setMembers(d.map((m: any) => ({ id: m.id, name: m.name, role_label: m.role_label, email: "" })));
      }
    } catch { /* ignore */ }
    setLoadingMembers(false);
  }, [nodeId, isPerson]);

  useEffect(() => {
    if (!isPerson) loadMembers();
  }, [loadMembers, isPerson]);

  // Autosave email on blur
  async function handleEmailBlur() {
    if (email === savedEmailRef.current) return;
    setSavingEmail(true);
    try {
      const token = localStorage.getItem("access_token");
      await fetch(`${API}/groups/${nodeId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ email: email.trim() }),
      });
      savedEmailRef.current = email.trim();
      // Also update parent canvas node data
      await onUpdate(nodeId, { email: email.trim() });
    } catch { /* ignore */ }
    setSavingEmail(false);
  }

  // Autosave context_notes on blur
  async function handleContextNotesBlur() {
    if (contextNotes === (data.contextNotes ?? "")) return;
    setSavingContext(true);
    try {
      const token = localStorage.getItem("access_token");
      await fetch(`${API}/groups/${nodeId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ context_notes: contextNotes || null }),
      });
    } catch { /* ignore */ }
    setSavingContext(false);
  }

  async function handleSave() {
    setSaving(true);
    if (isPerson) {
      await onUpdate(nodeId, { name, tarea_general: role, email: email.trim() });
    } else {
      await onUpdate(nodeId, { name, description, area, email: email.trim() });
    }
    savedEmailRef.current = email.trim();
    setSaving(false);
    onClose();
  }

  async function handleDelete() {
    if (!confirmDelete) { setConfirmDelete(true); return; }
    await onDelete(nodeId);
  }

  async function handleAddMember() {
    if (!newMemberName.trim()) return;
    setAddingMember(true);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API}/members`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ organization_id: orgId, group_id: nodeId, name: newMemberName, role_label: newMemberRole }),
      });
      if (res.ok) {
        setNewMemberName(""); setNewMemberRole("");
        await loadMembers();
      }
    } catch { /* ignore */ }
    setAddingMember(false);
  }

  async function handleRemoveMember(memberId: string) {
    try {
      const token = localStorage.getItem("access_token");
      await fetch(`${API}/members/${memberId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      setMembers((prev) => prev.filter((m) => m.id !== memberId));
    } catch { /* ignore */ }
  }

  return (
    <div className="absolute top-0 right-0 h-full w-80 bg-warm-50 border-l border-warm-200 shadow-warm-md z-10 flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between px-5 py-4 border-b border-warm-200 bg-white">
        <div className="flex-1 min-w-0 pr-2">
          <h3 className="font-display italic text-lg text-warm-900 leading-tight truncate">
            {data.label}
          </h3>
          {data.role && (
            <p className="text-xs text-warm-500 truncate mt-0.5">{data.role}</p>
          )}
        </div>
        <button onClick={onClose} className="text-warm-400 hover:text-warm-700 flex-shrink-0 mt-0.5">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs for area nodes */}
      {!isPerson && (
        <div className="flex border-b border-warm-200 bg-white">
          {(["info", "members"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2 text-xs font-medium text-center transition-colors relative ${
                tab === t ? "text-warm-900" : "text-warm-400 hover:text-warm-600"
              }`}
            >
              {t === "info" ? "Info" : `Miembros (${members.length})`}
              {tab === t && (
                <span className="absolute bottom-0 left-4 right-4 h-[2px] bg-accent rounded-full" />
              )}
            </button>
          ))}
        </div>
      )}

      {/* ── Info tab ── */}
      {tab === "info" && (
        <>
          <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
            {/* Name */}
            <div>
              <label className="block text-xs font-semibold text-warm-900 mb-1.5">
                {isPerson ? "Nombre completo" : "Nombre del área"}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={inputCls}
                placeholder={isPerson ? "Ej: Juan Pérez" : "Ej: Tecnología"}
              />
            </div>

            {isPerson ? (
              /* ── Person node fields ── */
              <>
                <div>
                  <label className="block text-xs font-semibold text-warm-900 mb-1.5">Cargo</label>
                  <input
                    type="text"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className={inputCls}
                    placeholder="Ej: Director de Tecnología"
                  />
                </div>

                {/* Email — autosave on blur */}
                <div>
                  <label className="block text-xs font-semibold text-warm-900 mb-1.5">
                    Email del miembro
                    {savingEmail && (
                      <span className="ml-2 text-[10px] text-warm-400 font-normal">guardando…</span>
                    )}
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onBlur={handleEmailBlur}
                    className={inputCls}
                    placeholder="correo@empresa.com"
                  />
                  <p className="mt-1 text-[10px] text-warm-400">
                    Este email recibirá la entrevista en la capa Recolección
                  </p>
                </div>
              </>
            ) : (
              /* ── Area node fields ── */
              <>
                <div>
                  <label className="block text-xs font-semibold text-warm-900 mb-1.5">Área / Categoría</label>
                  <input
                    type="text"
                    value={area}
                    onChange={(e) => setArea(e.target.value)}
                    className={inputCls}
                    placeholder="Ej: Tecnología"
                  />
                </div>

                {/* Email — autosave on blur */}
                <div>
                  <label className="block text-xs font-semibold text-warm-900 mb-1.5">
                    Email del miembro
                    {savingEmail && (
                      <span className="ml-2 text-[10px] text-warm-400 font-normal">guardando…</span>
                    )}
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onBlur={handleEmailBlur}
                    className={inputCls}
                    placeholder="correo@empresa.com"
                  />
                  <p className="mt-1 text-[10px] text-warm-400">
                    Quien responderá la entrevista por esta área
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-warm-900 mb-1.5">Descripción</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className={`${inputCls} resize-none`}
                    rows={3}
                    placeholder="Descripción opcional del área..."
                  />
                </div>
              </>
            )}

            {/* Context notes — autosave on blur */}
            <div>
              <label className="block text-xs font-semibold text-warm-900 mb-1.5">
                Contexto del nodo
                {savingContext && (
                  <span className="ml-2 text-[10px] text-warm-400 font-normal">guardando…</span>
                )}
              </label>
              <textarea
                value={contextNotes}
                onChange={(e) => setContextNotes(e.target.value)}
                onBlur={handleContextNotesBlur}
                className={`${inputCls} resize-none`}
                rows={4}
                placeholder="¿Qué hace este equipo? ¿Hay algo importante sobre su dinámica que debamos saber?"
              />
            </div>
          </div>

          {/* Footer actions */}
          <div className="px-5 py-4 border-t border-warm-200 bg-white space-y-2">
            <button
              onClick={handleSave}
              disabled={saving || !name.trim()}
              className="w-full py-2.5 bg-accent text-white text-sm font-semibold rounded-md hover:bg-accent-hover disabled:opacity-50 transition-colors"
            >
              {saving ? "Guardando…" : "Guardar cambios"}
            </button>
            <button
              onClick={handleDelete}
              className={`w-full flex items-center justify-center gap-1.5 py-1.5 text-xs transition-colors rounded-md ${
                confirmDelete ? "bg-red-600 text-white" : "text-red-500 hover:text-red-700"
              }`}
            >
              <Trash2 className="w-3 h-3" />
              {confirmDelete ? "Confirmar eliminación" : "Eliminar nodo"}
            </button>
          </div>
        </>
      )}

      {/* ── Members tab ── */}
      {tab === "members" && !isPerson && (
        <>
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {loadingMembers ? (
              <p className="text-center py-8 text-sm text-warm-400">Cargando…</p>
            ) : members.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-sm text-warm-400">Sin miembros</p>
                <p className="text-xs text-warm-300 mt-1">Agrega personas a esta área</p>
              </div>
            ) : (
              <div className="space-y-2">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center justify-between px-3 py-2.5 bg-white rounded-md border border-warm-200">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-warm-900 truncate">{m.name}</div>
                      {m.role_label && <div className="text-xs text-warm-500 truncate">{m.role_label}</div>}
                    </div>
                    <button
                      onClick={() => handleRemoveMember(m.id)}
                      className="text-warm-300 hover:text-red-500 flex-shrink-0 ml-2 transition-colors"
                    >
                      <UserMinus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="px-5 py-4 border-t border-warm-200 bg-white space-y-2">
            <input
              type="text"
              value={newMemberName}
              onChange={(e) => setNewMemberName(e.target.value)}
              className={inputCls}
              placeholder="Nombre"
            />
            <input
              type="text"
              value={newMemberRole}
              onChange={(e) => setNewMemberRole(e.target.value)}
              className={inputCls}
              placeholder="Cargo (opcional)"
            />
            <button
              onClick={handleAddMember}
              disabled={addingMember || !newMemberName.trim()}
              className="w-full py-2 bg-accent text-white text-sm font-semibold rounded-md hover:bg-accent-hover disabled:opacity-50 flex items-center justify-center gap-1.5 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              {addingMember ? "Agregando…" : "Agregar miembro"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
