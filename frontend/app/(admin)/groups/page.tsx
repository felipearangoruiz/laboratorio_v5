"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/apiFetch";

type SessionResponse = {
  organization_id: string | null;
  role: string;
  user_id: string;
};

type Group = {
  id: string;
  organization_id?: string;
  parent_group_id: string | null;
  name: string;
  description: string | null;
  nivel_jerarquico: number | null;
  tipo_nivel: string | null;
};

type GroupFormState = {
  name: string;
  description: string;
  nivel_jerarquico: string;
  tipo_nivel: string;
  parent_group_id: string;
};

const initialForm: GroupFormState = {
  name: "",
  description: "",
  nivel_jerarquico: "",
  tipo_nivel: "",
  parent_group_id: "",
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

export default function GroupsPage() {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<GroupFormState>(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const groupsById = useMemo(() => new Map(groups.map((group) => [group.id, group.name])), [groups]);

  async function loadGroups() {
    try {
      const groupList = await apiFetch<Group[]>("/groups");
      setGroups(Array.isArray(groupList) ? groupList : []);
    } catch (error: unknown) {
      setGroups([]);
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

        await loadGroups();
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
    setEditingGroupId(null);
    setFormError(null);
  }

  function openCreateForm() {
    resetForm();
    setShowForm(true);
  }

  function openEditForm(group: Group) {
    setEditingGroupId(group.id);
    setFormValues({
      name: group.name,
      description: group.description ?? "",
      nivel_jerarquico:
        group.nivel_jerarquico === null || group.nivel_jerarquico === undefined
          ? ""
          : String(group.nivel_jerarquico),
      tipo_nivel: group.tipo_nivel ?? "",
      parent_group_id: group.parent_group_id ?? "",
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
      description: formValues.description.trim() || null,
      nivel_jerarquico: formValues.nivel_jerarquico.trim()
        ? Number(formValues.nivel_jerarquico)
        : null,
      tipo_nivel: formValues.tipo_nivel.trim() || null,
      parent_group_id: formValues.parent_group_id || null,
    };

    try {
      if (editingGroupId) {
        await apiFetch(`/groups/${editingGroupId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch("/groups", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }

      await loadGroups();
      setShowForm(false);
      resetForm();
    } catch (error: unknown) {
      setFormError(getErrorDetail(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(groupId: string) {
    const shouldDelete = window.confirm("¿Seguro que deseas eliminar este grupo?");
    if (!shouldDelete) {
      return;
    }

    try {
      await apiFetch(`/groups/${groupId}`, { method: "DELETE" });
      await loadGroups();

      if (editingGroupId === groupId) {
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
        <h1 className="text-2xl font-semibold text-gray-900">Grupos</h1>
        <p className="mt-2 text-sm text-gray-600">
          Administra la estructura organizacional creando y editando grupos y sus jerarquías.
        </p>
      </header>

      <div className="mb-4">
        <button
          type="button"
          onClick={openCreateForm}
          className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          Nuevo grupo
        </button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            {editingGroupId ? "Editar grupo" : "Crear grupo"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="group-name" className="mb-1 block text-sm font-medium text-gray-700">
                Nombre
              </label>
              <input
                id="group-name"
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
              <label htmlFor="group-description" className="mb-1 block text-sm font-medium text-gray-700">
                Descripción
              </label>
              <input
                id="group-description"
                type="text"
                value={formValues.description}
                onChange={(event) =>
                  setFormValues((prev) => ({
                    ...prev,
                    description: event.target.value,
                  }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label htmlFor="group-level" className="mb-1 block text-sm font-medium text-gray-700">
                  Nivel jerárquico
                </label>
                <input
                  id="group-level"
                  type="number"
                  value={formValues.nivel_jerarquico}
                  onChange={(event) =>
                    setFormValues((prev) => ({
                      ...prev,
                      nivel_jerarquico: event.target.value,
                    }))
                  }
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="group-type" className="mb-1 block text-sm font-medium text-gray-700">
                  Tipo de nivel
                </label>
                <input
                  id="group-type"
                  type="text"
                  value={formValues.tipo_nivel}
                  onChange={(event) =>
                    setFormValues((prev) => ({
                      ...prev,
                      tipo_nivel: event.target.value,
                    }))
                  }
                  placeholder="ej: dirección, área, equipo"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label htmlFor="group-parent" className="mb-1 block text-sm font-medium text-gray-700">
                Grupo padre
              </label>
              <select
                id="group-parent"
                value={formValues.parent_group_id}
                onChange={(event) =>
                  setFormValues((prev) => ({
                    ...prev,
                    parent_group_id: event.target.value,
                  }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
              >
                <option value="">Ninguno</option>
                {groups
                  .filter((group) => group.id !== editingGroupId)
                  .map((group) => (
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
                {submitting ? "Guardando..." : editingGroupId ? "Guardar cambios" : "Crear grupo"}
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

      {!loading && !generalError && groups.length === 0 ? (
        <p className="text-sm text-gray-600">No hay grupos creados aún.</p>
      ) : null}

      {!loading && !generalError && groups.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Nombre</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Descripción</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Nivel jerárquico</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Tipo</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Grupo padre</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {groups.map((group) => {
                const parentName = group.parent_group_id ? groupsById.get(group.parent_group_id) || "—" : "—";

                return (
                  <tr key={group.id}>
                    <td className="px-4 py-3 text-gray-900">{group.name}</td>
                    <td className="px-4 py-3 text-gray-700">{group.description || "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{group.nivel_jerarquico ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{group.tipo_nivel || "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{parentName}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => openEditForm(group)}
                          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(group.id)}
                          className="rounded-md border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
