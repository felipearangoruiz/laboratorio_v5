"use client";

import { useState, useEffect, useCallback } from "react";
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
  };
  onUpdate: (nodeId: string, data: Record<string, any>) => Promise<void>;
  onDelete: (nodeId: string) => Promise<void>;
  onClose: () => void;
}

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
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Members state (for area nodes)
  const [members, setMembers] = useState<NodeMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [newMemberName, setNewMemberName] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("");
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [addingMember, setAddingMember] = useState(false);

  useEffect(() => {
    setName(data.label);
    setRole(data.role);
    setEmail(data.email || "");
    setArea(data.area);
    setConfirmDelete(false);
    setTab("info");
  }, [nodeId, data]);

  const loadMembers = useCallback(async () => {
    if (isPerson) return;
    setLoadingMembers(true);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/groups/${nodeId}/members`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setMembers(data.map((m: any) => ({
          id: m.id,
          name: m.name,
          role_label: m.role_label,
          email: "",
        })));
      }
    } catch { /* ignore */ }
    setLoadingMembers(false);
  }, [nodeId, isPerson]);

  useEffect(() => {
    if (!isPerson) loadMembers();
  }, [loadMembers, isPerson]);

  async function handleSave() {
    setSaving(true);
    if (isPerson) {
      await onUpdate(nodeId, {
        name,
        tarea_general: role,
        email,
      });
    } else {
      await onUpdate(nodeId, {
        name,
        description,
        area,
      });
    }
    setSaving(false);
    onClose();
  }

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    await onDelete(nodeId);
  }

  async function handleAddMember() {
    if (!newMemberName.trim()) return;
    setAddingMember(true);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/members`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            organization_id: orgId,
            group_id: nodeId,
            name: newMemberName,
            role_label: newMemberRole,
          }),
        }
      );
      if (res.ok) {
        setNewMemberName("");
        setNewMemberRole("");
        setNewMemberEmail("");
        await loadMembers();
      }
    } catch { /* ignore */ }
    setAddingMember(false);
  }

  async function handleRemoveMember(memberId: string) {
    try {
      const token = localStorage.getItem("access_token");
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/members/${memberId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setMembers((prev) => prev.filter((m) => m.id !== memberId));
    } catch { /* ignore */ }
  }

  return (
    <div className="absolute top-0 right-0 h-full w-80 bg-white border-l border-gray-200 shadow-lg z-10 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">
          {isPerson ? "Editar persona" : "Editar área"}
        </h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs for area nodes */}
      {!isPerson && (
        <div className="flex border-b border-gray-100">
          <button
            onClick={() => setTab("info")}
            className={`flex-1 py-2 text-xs font-medium text-center transition-colors ${
              tab === "info"
                ? "text-gray-900 border-b-2 border-gray-900"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Info
          </button>
          <button
            onClick={() => setTab("members")}
            className={`flex-1 py-2 text-xs font-medium text-center transition-colors ${
              tab === "members"
                ? "text-gray-900 border-b-2 border-gray-900"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Miembros ({members.length})
          </button>
        </div>
      )}

      {/* Info tab */}
      {tab === "info" && (
        <>
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                {isPerson ? "Nombre completo" : "Nombre del área"}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
                placeholder={isPerson ? "Ej: Juan Pérez" : "Ej: Tecnología"}
              />
            </div>

            {isPerson ? (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Cargo
                  </label>
                  <input
                    type="text"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
                    placeholder="Ej: Director de Tecnología"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
                    placeholder="Ej: juan@empresa.com"
                  />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Área / Categoría
                  </label>
                  <input
                    type="text"
                    value={area}
                    onChange={(e) => setArea(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
                    placeholder="Ej: Tecnología"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Descripción
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none resize-none"
                    rows={3}
                    placeholder="Descripción opcional del área..."
                  />
                </div>
              </>
            )}
          </div>

          {/* Actions */}
          <div className="px-4 py-3 border-t border-gray-100 space-y-2">
            <button
              onClick={handleSave}
              disabled={saving || !name.trim()}
              className="w-full py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              {saving ? "Guardando..." : "Guardar cambios"}
            </button>
            <button
              onClick={handleDelete}
              className={`w-full py-2 text-sm font-medium rounded-lg flex items-center justify-center gap-1.5 ${
                confirmDelete
                  ? "bg-red-600 text-white hover:bg-red-700"
                  : "text-red-600 border border-red-200 hover:bg-red-50"
              }`}
            >
              <Trash2 className="w-3.5 h-3.5" />
              {confirmDelete ? "Confirmar eliminación" : "Eliminar nodo"}
            </button>
          </div>
        </>
      )}

      {/* Members tab (area only) */}
      {tab === "members" && !isPerson && (
        <>
          <div className="flex-1 overflow-y-auto px-4 py-4">
            {loadingMembers ? (
              <div className="text-center py-8 text-sm text-gray-400">Cargando...</div>
            ) : members.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-sm text-gray-400">Sin miembros</p>
                <p className="text-xs text-gray-400 mt-1">
                  Agrega personas a esta área
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {members.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {m.name}
                      </div>
                      {m.role_label && (
                        <div className="text-xs text-gray-500 truncate">
                          {m.role_label}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => handleRemoveMember(m.id)}
                      className="text-gray-400 hover:text-red-500 flex-shrink-0 ml-2"
                      title="Eliminar miembro"
                    >
                      <UserMinus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add member form */}
          <div className="px-4 py-3 border-t border-gray-100 space-y-2">
            <input
              type="text"
              value={newMemberName}
              onChange={(e) => setNewMemberName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
              placeholder="Nombre"
            />
            <input
              type="text"
              value={newMemberRole}
              onChange={(e) => setNewMemberRole(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
              placeholder="Cargo (opcional)"
            />
            <button
              onClick={handleAddMember}
              disabled={addingMember || !newMemberName.trim()}
              className="w-full py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              {addingMember ? "Agregando..." : "Agregar miembro"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
