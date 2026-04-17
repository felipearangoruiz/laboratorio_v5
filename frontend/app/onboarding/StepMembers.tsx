"use client";

import type { MemberEntry } from "./page";
import { ArrowLeft, ArrowRight, Plus, Trash2 } from "lucide-react";

interface Props {
  members: MemberEntry[];
  setMembers: (m: MemberEntry[]) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function StepMembers({
  members,
  setMembers,
  onNext,
  onBack,
}: Props) {
  function update(index: number, field: keyof MemberEntry, value: string) {
    const updated = [...members];
    updated[index] = { ...updated[index], [field]: value };
    setMembers(updated);
  }

  function addMember() {
    if (members.length < 5) {
      setMembers([...members, { name: "", role_label: "", email: "" }]);
    }
  }

  function removeMember(index: number) {
    if (members.length > 3) {
      setMembers(members.filter((_, i) => i !== index));
    }
  }

  const validMembers = members.filter(
    (m) => m.name.trim() && m.email.trim(),
  );
  const canProceed = validMembers.length >= 3;

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900">Invita a tu equipo</h2>
      <p className="mt-1 text-sm text-gray-500">
        Ingresa entre 3 y 5 miembros. Recibirán un enlace para responder una
        encuesta corta.
      </p>

      <div className="mt-6 space-y-3">
        {members.map((m, i) => (
          <div
            key={i}
            className="rounded-lg border border-gray-200 bg-white p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-gray-400">
                Miembro {i + 1}
              </span>
              {members.length > 3 && (
                <button
                  type="button"
                  onClick={() => removeMember(i)}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <input
                type="text"
                placeholder="Nombre"
                value={m.name}
                onChange={(e) => update(i, "name", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-brand-500"
              />
              <input
                type="text"
                placeholder="Rol (opcional)"
                value={m.role_label}
                onChange={(e) => update(i, "role_label", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-brand-500"
              />
              <input
                type="email"
                placeholder="correo@ejemplo.com"
                value={m.email}
                onChange={(e) => update(i, "email", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-brand-500"
              />
            </div>
          </div>
        ))}
      </div>

      {members.length < 5 && (
        <button
          type="button"
          onClick={addMember}
          className="mt-3 inline-flex items-center gap-1 text-sm text-brand-600 hover:text-brand-700"
        >
          <Plus className="h-4 w-4" />
          Agregar miembro
        </button>
      )}

      <p className="mt-2 text-xs text-gray-400">
        {validMembers.length} de {members.length} miembros completos
        {validMembers.length < 3 && " (mínimo 3)"}
      </p>

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Atrás
        </button>
        <button
          onClick={onNext}
          disabled={!canProceed}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40 transition-colors"
        >
          Enviar invitaciones
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
