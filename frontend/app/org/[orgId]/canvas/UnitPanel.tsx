"use client";

// ============================================================
// Sprint 2.B — UnitPanel
// ============================================================
// Panel contextual de capa Estructura para nodos type='unit'
// (áreas). Reemplaza a SidePanel legacy. Consume Node +
// NodeState del modelo nuevo; las ediciones van al compat layer
// (updateGroup, createGroup) o al endpoint nativo (updateNode
// para attrs.admin_notes).

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronRight, Loader2, Plus, X } from "lucide-react";
import {
  createGroup,
  updateGroup,
  updateNode,
} from "@/lib/api";
import { mapNodeStateToLegacyStatus } from "@/lib/view-models/legacyOrgNodeAdapter";
import { computeAreaStatus } from "@/lib/view-models/areaStatus";
import type { Node as ModelNode, NodeState } from "@/lib/types";

interface UnitPanelProps {
  node: ModelNode;
  childPersons: ModelNode[];
  nodeStates: NodeState[];
  activeCampaignId: string | null;
  onClose: () => void;
  onSelectNode: (nodeId: string) => void;
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

function StatusDot({ status }: { status: string }) {
  const color =
    status === "completed"
      ? "bg-emerald-500"
      : status === "in_progress"
        ? "bg-amber-500"
        : status === "pending"
          ? "bg-warm-400"
          : status === "expired"
            ? "bg-warm-300"
            : "bg-warm-200";
  return <span className={`inline-block w-2 h-2 rounded-full ${color}`} />;
}

function AreaBadge({
  label,
  total,
  completed,
}: {
  label: "empty" | "incomplete" | "complete";
  total: number;
  completed: number;
}) {
  const map = {
    empty: { text: "Vacío", cls: "bg-warm-100 text-warm-600" },
    incomplete: { text: "Incompleto", cls: "bg-amber-100 text-amber-700" },
    complete: { text: "Completo", cls: "bg-emerald-100 text-emerald-700" },
  };
  const { text, cls } = map[label];
  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${cls}`}
      >
        {text}
      </span>
      {total > 0 && (
        <span className="text-xs text-warm-500">
          {completed} de {total} miembros respondieron
        </span>
      )}
    </div>
  );
}

export default function UnitPanel({
  node,
  childPersons,
  nodeStates,
  activeCampaignId,
  onClose,
  onSelectNode,
  onDelete,
  onRefetch,
}: UnitPanelProps) {
  const attrs = (node.attrs ?? {}) as Record<string, unknown>;
  const initialName = node.name;
  const initialDescription = (attrs.description as string) ?? "";
  const initialNotes = (attrs.admin_notes as string) ?? "";

  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [adminNotes, setAdminNotes] = useState(initialNotes);

  const [nameState, setNameState] = useState<SaveState>("idle");
  const [descState, setDescState] = useState<SaveState>("idle");
  const [notesState, setNotesState] = useState<SaveState>("idle");

  // Add-member form
  const [addOpen, setAddOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  useEffect(() => {
    setName(initialName);
    setDescription(initialDescription);
    setAdminNotes(initialNotes);
    setNameState("idle");
    setDescState("idle");
    setNotesState("idle");
    setAddOpen(false);
    setNewName("");
    setNewRole("");
    setNewEmail("");
    setAddError(null);
  }, [node.id, initialName, initialDescription, initialNotes]);

  const savedRef = useRef({
    name: initialName,
    description: initialDescription,
    adminNotes: initialNotes,
  });

  useEffect(() => {
    savedRef.current = {
      name: initialName,
      description: initialDescription,
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

  // Description autosave
  useEffect(() => {
    if (description === savedRef.current.description) return;
    const t = setTimeout(async () => {
      setDescState("saving");
      try {
        await updateGroup(node.id, { description });
        savedRef.current.description = description;
        setSavedFlash(setDescState);
        await onRefetch();
      } catch {
        setDescState("error");
      }
    }, 1000);
    return () => clearTimeout(t);
  }, [description, node.id, onRefetch, setSavedFlash]);

  // admin_notes autosave vía PATCH /nodes nativo.
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

  const area = computeAreaStatus(
    node,
    childPersons,
    nodeStates,
    activeCampaignId,
  );

  async function handleAddMember() {
    if (!newName.trim() || !newRole.trim()) {
      setAddError("Nombre y rol son obligatorios.");
      return;
    }
    setAdding(true);
    setAddError(null);
    try {
      await createGroup({
        organization_id: node.organization_id,
        node_type: "person",
        name: newName.trim(),
        tarea_general: newRole.trim(),
        email: newEmail.trim() || undefined,
        parent_group_id: node.id,
        position_x: node.position_x + 80,
        position_y: node.position_y + 120,
      });
      await onRefetch();
      setAddOpen(false);
      setNewName("");
      setNewRole("");
      setNewEmail("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "No se pudo crear el miembro";
      setAddError(msg);
    } finally {
      setAdding(false);
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
            placeholder="Nombre del área"
          />
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] uppercase tracking-wide text-warm-400">
              Área
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
        {/* Descripción */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs uppercase tracking-wide text-warm-500">
              Descripción
            </h3>
            <SaveIndicator state={descState} />
          </div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className={`${inputCls} resize-y`}
            placeholder="Describe el propósito del área."
          />
        </section>

        {/* Estado del área */}
        <section>
          <h3 className="text-xs uppercase tracking-wide text-warm-500 mb-2">
            Estado del área
          </h3>
          <AreaBadge
            label={area.label}
            total={area.total}
            completed={area.completed}
          />
        </section>

        {/* Archivos del nodo */}
        <section>
          <h3 className="text-xs uppercase tracking-wide text-warm-500 mb-2">
            Archivos del nodo
          </h3>
          <div className="text-sm text-gray-500 italic">
            Archivos disponibles en el próximo sprint.
          </div>
        </section>

        {/* Miembros */}
        <section>
          <h3 className="text-xs uppercase tracking-wide text-warm-500 mb-2">
            Miembros
          </h3>
          <ul className="divide-y divide-warm-100 border border-warm-200 rounded-md overflow-hidden">
            {childPersons.length === 0 && (
              <li className="px-3 py-3 text-sm text-warm-500 italic">
                Sin miembros aún.
              </li>
            )}
            {childPersons.map((p) => {
              const pAttrs = (p.attrs ?? {}) as Record<string, unknown>;
              const pRole = (pAttrs.tarea_general as string) ?? "";
              const ns = nodeStates.find(
                (s) =>
                  s.node_id === p.id &&
                  (!activeCampaignId || s.campaign_id === activeCampaignId),
              );
              const status = mapNodeStateToLegacyStatus(
                ns?.status,
                pAttrs.token_status,
              );
              return (
                <li key={p.id}>
                  <button
                    onClick={() => onSelectNode(p.id)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-warm-50 text-left transition-colors"
                  >
                    <StatusDot status={status} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-warm-900 truncate">
                        {p.name}
                      </div>
                      {pRole && (
                        <div className="text-xs text-warm-500 truncate">
                          {pRole}
                        </div>
                      )}
                    </div>
                    <ChevronRight className="w-4 h-4 text-warm-400" />
                  </button>
                </li>
              );
            })}
          </ul>

          {!addOpen ? (
            <button
              onClick={() => setAddOpen(true)}
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
            >
              <Plus className="w-3.5 h-3.5" /> Agregar miembro
            </button>
          ) : (
            <div className="mt-3 space-y-2 border border-warm-200 rounded-md p-3 bg-warm-50/40">
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className={inputCls}
                placeholder="Nombre (obligatorio)"
              />
              <input
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className={inputCls}
                placeholder="Rol (obligatorio)"
              />
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className={inputCls}
                placeholder="Correo (opcional)"
              />
              {addError && (
                <p className="text-xs text-rose-600">{addError}</p>
              )}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleAddMember}
                  disabled={adding}
                  className="px-3 py-1.5 rounded-md bg-accent text-white text-sm hover:bg-accent-hover disabled:opacity-50"
                >
                  {adding ? "Creando…" : "Crear"}
                </button>
                <button
                  onClick={() => {
                    setAddOpen(false);
                    setAddError(null);
                  }}
                  className="px-3 py-1.5 rounded-md border border-warm-300 text-sm text-warm-600"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </section>

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
              Eliminar área
            </button>
          </section>
        )}
      </div>
    </aside>
  );
}
