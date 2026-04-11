"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/apiFetch";

type SessionResponse = {
  organization_id: string | null;
  role: string;
  user_id: string;
};

type Group = {
  id: string;
  name: string;
};

type Member = {
  id: string;
  name: string;
  role_label: string | null;
  group_id: string | null;
  token_status: "pending" | "in_progress" | "completed" | "expired";
  interview_token: string;
  created_at: string;
};

type MemberFormState = {
  name: string;
  role_label: string;
  group_id: string;
};

const initialForm: MemberFormState = {
  name: "",
  role_label: "",
  group_id: "",
};

function getErrorDetail(error: unknown): string {
  if (typeof error === "object" && error !== null) {
    const detail = (error as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    const message = (error as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Ocurrió un error inesperado. Intenta nuevamente.";
}

function getTokenStatusBadgeClass(status: Member["token_status"]): string {
  if (status === "in_progress") {
    return "bg-yellow-100 text-yellow-800";
  }

  if (status === "completed") {
    return "bg-green-100 text-green-800";
  }

  if (status === "expired") {
    return "bg-red-100 text-red-700";
  }

  return "bg-gray-100 text-gray-700";
}

export default function MembersPage() {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingMemberId, setEditingMemberId] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<MemberFormState>(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const groupsById = useMemo(() => new Map(groups.map((group) => [group.id, group.name])), [groups]);

  async function loadMembersAndGroups(organizationId: string) {
    try {
      const [memberList, groupList] = await Promise.all([
        apiFetch<Member[]>(`/organizations/${organizationId}/members`),
        apiFetch<Group[]>("/groups"),
      ]);

      setMembers(memberList);
      setGroups(groupList);
    } catch (error: unknown) {
      setGeneralError(getErrorDetail(error));
    }
  }

  useEffect(() => {
    async function bootstrap() {
      setLoading(true);
      setGeneralError(null);

      try {
        const currentSession = await apiFetch<SessionResponse>("/auth/me");
        setSession(currentSession);

        if (!currentSession.organization_id) {
          setGeneralError("No se encontró una organización asociada a tu sesión.");
          return;
        }

        await loadMembersAndGroups(currentSession.organization_id);
      } catch (error: unknown) {
        setGeneralError(getErrorDetail(error));
      } finally {
        setLoading(false);
      }
    }

    bootstrap();
  }, []);

  function resetForm() {
    setFormValues(initialForm);
    setEditingMemberId(null);
    setFormError(null);
  }

  function openCreateForm() {
    resetForm();
    setShowForm(true);
  }

  function openEditForm(member: Member) {
    setEditingMemberId(member.id);
    setFormValues({
      name: member.name,
      role_label: member.role_label ?? "",
      group_id: member.group_id ?? "",
    });
    setFormError(null);
    setShowForm(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!session?.organization_id) {
      setFormError("No se encontró una organización asociada a tu sesión.");
      return;
    }

    if (!formValues.name.trim()) {
      setFormError("El nombre es obligatorio.");
      return;
    }

    setSubmitting(true);
    setFormError(null);

    const payload = {
      organization_id: session.organization_id,
      name: formValues.name.trim(),
      role_label: formValues.role_label.trim(),
      group_id: formValues.group_id || null,
    };

    try {
      if (editingMemberId) {
        await apiFetch(`/members/${editingMemberId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch("/members", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }

      await loadMembersAndGroups(session.organization_id);
      setShowForm(false);
      resetForm();
    } catch (error: unknown) {
      setFormError(getErrorDetail(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(memberId: string) {
    const shouldDelete = window.confirm("¿Seguro que deseas eliminar este miembro?");
    if (!shouldDelete) {
      return;
    }

    if (!session?.organization_id) {
      setGeneralError("No se encontró una organización asociada a tu sesión.");
      return;
    }

    try {
      await apiFetch(`/members/${memberId}`, { method: "DELETE" });
      await loadMembersAndGroups(session.organization_id);

      if (editingMemberId === memberId) {
        setShowForm(false);
        resetForm();
      }
    } catch (error: unknown) {
      setGeneralError(getErrorDetail(error));
    }
  }

  return (
    <section className="p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Miembros</h1>
        <p className="mt-2 text-sm text-gray-600">
          Gestiona los miembros de tu organización y su asignación a grupos.
        </p>
      </header>

      <div className="mb-4">
        <button
          type="button"
          onClick={openCreateForm}
          className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          Nuevo miembro
        </button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            {editingMemberId ? "Editar miembro" : "Crear miembro"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="member-name" className="mb-1 block text-sm font-medium text-gray-700">
                Nombre
              </label>
              <input
                id="member-name"
                type="text"
                value={formValues.name}
                onChange={(event) =>
                  setFormValues((prev) => ({
                    ...prev,
                    name: event.target.value,
                  }))
                }
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="member-role" className="mb-1 block text-sm font-medium text-gray-700">
                Rol / cargo
              </label>
              <input
                id="member-role"
                type="text"
                value={formValues.role_label}
                onChange={(event) =>
                  setFormValues((prev) => ({
                    ...prev,
                    role_label: event.target.value,
                  }))
                }
                placeholder="ej: vendedor, administrador"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="member-group" className="mb-1 block text-sm font-medium text-gray-700">
                Grupo
              </label>
              <select
                id="member-group"
                value={formValues.group_id}
                onChange={(event) =>
                  setFormValues((prev) => ({
                    ...prev,
                    group_id: event.target.value,
                  }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
              >
                <option value="">Sin grupo</option>
                {groups.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </select>
            </div>

            {formError && <p className="text-sm text-red-600">{formError}</p>}

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={submitting}
                className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:bg-gray-500"
              >
                {submitting ? "Guardando..." : editingMemberId ? "Guardar cambios" : "Crear miembro"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  resetForm();
                }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? <p className="text-sm text-gray-600">Cargando...</p> : null}
      {!loading && generalError ? <p className="mb-4 text-sm text-red-600">{generalError}</p> : null}

      {!loading && !generalError && members.length === 0 ? (
        <p className="text-sm text-gray-600">No hay miembros creados aún.</p>
      ) : null}

      {!loading && !generalError && members.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Nombre</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Rol</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Grupo</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Estado del token</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Token</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Abrir</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Fecha de creación</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {members.map((member) => (
                <tr key={member.id}>
                  <td className="px-4 py-3 text-gray-900">{member.name}</td>
                  <td className="px-4 py-3 text-gray-700">{member.role_label || "—"}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {member.group_id ? groupsById.get(member.group_id) || "—" : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${getTokenStatusBadgeClass(
                        member.token_status
                      )}`}
                    >
                      {member.token_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">{member.interview_token}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/entrevista/${member.interview_token}`}
                      className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Abrir entrevista
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {new Date(member.created_at).toLocaleDateString("es-ES")}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => openEditForm(member)}
                        className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(member.id)}
                        className="rounded-md border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
                      >
                        Eliminar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
