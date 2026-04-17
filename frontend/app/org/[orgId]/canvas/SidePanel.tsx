"use client";

import { useState, useEffect } from "react";
import { X, Trash2 } from "lucide-react";

interface SidePanelProps {
  nodeId: string;
  data: {
    label: string;
    area: string;
    role: string;
    level: number | null;
  };
  onUpdate: (nodeId: string, data: Record<string, any>) => Promise<void>;
  onDelete: (nodeId: string) => Promise<void>;
  onClose: () => void;
}

export default function SidePanel({
  nodeId,
  data,
  onUpdate,
  onDelete,
  onClose,
}: SidePanelProps) {
  const [name, setName] = useState(data.label);
  const [role, setRole] = useState(data.role);
  const [area, setArea] = useState(data.area);
  const [level, setLevel] = useState<string>(
    data.level != null ? String(data.level) : ""
  );
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setName(data.label);
    setRole(data.role);
    setArea(data.area);
    setLevel(data.level != null ? String(data.level) : "");
    setConfirmDelete(false);
  }, [nodeId, data]);

  async function handleSave() {
    setSaving(true);
    await onUpdate(nodeId, {
      name,
      tarea_general: role,
      area,
      nivel_jerarquico: level ? parseInt(level, 10) : null,
    });
    setSaving(false);
  }

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    await onDelete(nodeId);
  }

  return (
    <div className="absolute top-0 right-0 h-full w-80 bg-white border-l border-gray-200 shadow-lg z-10 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">Editar nodo</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Nombre
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Rol / Cargo
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
            Área
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
            Nivel jerárquico
          </label>
          <input
            type="number"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
            placeholder="0 = raíz, 1 = dirección, 2 = gerencia..."
            min={0}
          />
        </div>
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
    </div>
  );
}
