import { redirect } from "next/navigation";
import { getSessionPayload } from "@/lib/session";
import { serverFetch } from "@/lib/serverFetch";

type Member = {
  id: string;
  name: string;
  role_label: string;
  group_id: string | null;
  token_status: "pending" | "in_progress" | "completed" | "expired";
  interview_token: string;
  created_at: string;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Ocurrió un error inesperado";
}

function getTokenStatusBadgeClass(status: Member["token_status"]): string {
  if (status === "in_progress") {
    return "bg-yellow-200 text-yellow-800";
  }

  if (status === "completed") {
    return "bg-green-200 text-green-800";
  }

  if (status === "expired") {
    return "bg-red-200 text-red-800";
  }

  return "bg-gray-200 text-gray-800";
}

export default async function MembersPage() {
  try {
    const session = await getSessionPayload();

    if (!session || !session.organization_id) {
      redirect("/login");
    }

    const members = await serverFetch<Member[]>(
      `/organizations/${session.organization_id}/members`
    );

    if (members.length === 0) {
      return <p className="text-sm text-gray-600">No hay miembros aún</p>;
    }

    return (
      <section className="space-y-6">
        <h1 className="text-2xl font-semibold text-gray-900">Miembros</h1>

        <div className="overflow-x-auto rounded-xl bg-white shadow">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Nombre</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Rol</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Grupo</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Estado del token</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Token</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Fecha de creación</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {members.map((member) => (
                <tr key={member.id}>
                  <td className="px-4 py-3 text-gray-900">{member.name}</td>
                  <td className="px-4 py-3 text-gray-700">{member.role_label || "—"}</td>
                  <td className="px-4 py-3 text-gray-700">{member.group_id || "—"}</td>
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
                  <td className="px-4 py-3 text-gray-700">
                    {new Date(member.created_at).toLocaleDateString("es-ES")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    );
  } catch (error: unknown) {
    return <p className="text-red-600">{getErrorMessage(error)}</p>;
  }
}
