"use client";

import { useState } from "react";
import { Plus, X, Send } from "lucide-react";
import type { QuickAssessmentMemberInvite } from "@/lib/types";

interface Props {
  onFinish: (members: QuickAssessmentMemberInvite[]) => void;
  onBack: () => void;
  loading: boolean;
}

export default function StepAddMembers({ onFinish, onBack, loading }: Props) {
  const [members, setMembers] = useState<QuickAssessmentMemberInvite[]>([
    { name: "", role: "", email: "" },
  ]);

  function updateMember(
    index: number,
    field: keyof QuickAssessmentMemberInvite,
    value: string
  ) {
    const updated = [...members];
    updated[index] = { ...updated[index], [field]: value };
    setMembers(updated);
  }

  function addMember() {
    if (members.length < 10) {
      setMembers([...members, { name: "", role: "", email: "" }]);
    }
  }

  function removeMember(index: number) {
    if (members.length > 1) {
      setMembers(members.filter((_, i) => i !== index));
    }
  }

  const validMembers = members.filter(
    (m) => m.name.trim() && m.email.trim() && m.email.includes("@")
  );

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900">
        Invita a tu equipo
      </h2>
      <p className="mt-2 text-sm text-gray-500">
        Agrega entre 3 y 5 miembros. Cada uno recibirá un enlace para responder
        una encuesta corta de forma anónima.
      </p>

      <div className="mt-6 space-y-4">
        {members.map((member, i) => (
          <div key={i} className="flex gap-2 items-start">
            <div className="flex-1 grid grid-cols-3 gap-2">
              <input
                type="text"
                placeholder="Nombre"
                value={member.name}
                onChange={(e) => updateMember(i, "name", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
              />
              <input
                type="text"
                placeholder="Rol"
                value={member.role}
                onChange={(e) => updateMember(i, "role", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
              />
              <input
                type="email"
                placeholder="correo@email.com"
                value={member.email}
                onChange={(e) => updateMember(i, "email", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
              />
            </div>
            {members.length > 1 && (
              <button
                onClick={() => removeMember(i)}
                className="mt-2 text-gray-400 hover:text-red-500"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>

      {members.length < 10 && (
        <button
          onClick={addMember}
          className="mt-3 inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900"
        >
          <Plus className="w-4 h-4" />
          Agregar miembro
        </button>
      )}

      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-xs text-blue-700">
          Necesitas al menos 3 respuestas de miembros para generar el score
          radar. Puedes invitar más personas después.
        </p>
      </div>

      <div className="mt-8 flex gap-3">
        <button
          onClick={onBack}
          className="px-4 py-2.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Atrás
        </button>
        <button
          onClick={() => onFinish(validMembers)}
          disabled={loading || validMembers.length < 3}
          className="flex-1 inline-flex items-center justify-center gap-2 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
          {loading ? "Enviando invitaciones..." : `Enviar invitaciones (${validMembers.length})`}
        </button>
      </div>

      {validMembers.length < 3 && (
        <p className="mt-2 text-xs text-gray-400 text-center">
          Agrega al menos 3 miembros válidos ({validMembers.length}/3 mínimo)
        </p>
      )}
    </div>
  );
}
