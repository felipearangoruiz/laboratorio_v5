import { redirect } from "next/navigation";
import { getSessionPayload } from "@/lib/session";
import { serverFetch } from "@/lib/serverFetch";

type OrganizationStats = {
  total_members: number;
  total_groups: number;
  completed_interviews: number;
  pending_interviews: number;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Ocurrió un error inesperado";
}

export default async function AdminPage() {
  try {
    const session = await getSessionPayload();

    if (!session || !session.organization_id) {
      redirect("/login");
    }

    const stats = await serverFetch<OrganizationStats>(
      `/organizations/${session.organization_id}/stats`
    );

    return (
      <section className="space-y-6">
        <h1 className="text-2xl font-semibold text-gray-900">Resumen general</h1>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <article className="rounded-xl bg-white p-6 shadow">
            <p className="text-3xl font-bold text-gray-900">{stats.total_members}</p>
            <p className="mt-1 text-sm text-gray-600">Total miembros</p>
          </article>

          <article className="rounded-xl bg-white p-6 shadow">
            <p className="text-3xl font-bold text-gray-900">{stats.total_groups}</p>
            <p className="mt-1 text-sm text-gray-600">Grupos</p>
          </article>

          <article className="rounded-xl bg-white p-6 shadow">
            <p className="text-3xl font-bold text-gray-900">{stats.completed_interviews}</p>
            <p className="mt-1 text-sm text-gray-600">Entrevistas completadas</p>
          </article>

          <article className="rounded-xl bg-white p-6 shadow">
            <p className="text-3xl font-bold text-gray-900">{stats.pending_interviews}</p>
            <p className="mt-1 text-sm text-gray-600">Entrevistas pendientes</p>
          </article>
        </div>
      </section>
    );
  } catch (error: unknown) {
    return <p className="text-red-600">{getErrorMessage(error)}</p>;
  }
}
