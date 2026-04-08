import { redirect } from "next/navigation";
import { getSessionPayload } from "@/lib/session";
import { serverFetch } from "@/lib/serverFetch";

type Group = {
  id: string;
  parent_group_id: string | null;
  name: string;
  description: string;
  nivel_jerarquico: number | null;
  tipo_nivel: string | null;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Ocurrió un error inesperado";
}

export default async function GroupsPage() {
  try {
    const session = await getSessionPayload();

    if (!session || !session.organization_id) {
      redirect("/login");
    }

    const groups = await serverFetch<Group[]>("/groups");
    const groupsById = new Map(groups.map((group) => [group.id, group.name]));

    if (groups.length === 0) {
      return <p className="text-sm text-gray-600">No hay grupos aún</p>;
    }

    return (
      <section className="space-y-6">
        <h1 className="text-2xl font-semibold text-gray-900">Grupos</h1>

        <div className="overflow-x-auto rounded-xl bg-white shadow">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Nombre</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Descripción</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Nivel jerárquico</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Tipo</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Grupo padre</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Miembros</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {groups.map((group) => {
                const parentName = group.parent_group_id
                  ? groupsById.get(group.parent_group_id) || "—"
                  : "—";

                return (
                  <tr key={group.id}>
                    <td className="px-4 py-3 text-gray-900">{group.name}</td>
                    <td className="px-4 py-3 text-gray-700">{group.description || "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{group.nivel_jerarquico ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{group.tipo_nivel || "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{parentName}</td>
                    <td className="px-4 py-3 text-gray-700">—</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    );
  } catch (error: unknown) {
    return <p className="text-red-600">{getErrorMessage(error)}</p>;
  }
}
