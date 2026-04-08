import { redirect } from "next/navigation";
import TreeNode, { type TreeNodeType } from "@/components/TreeNode";
import { serverFetch } from "@/lib/serverFetch";
import { getSessionPayload } from "@/lib/session";

export default async function StructurePage() {
  const session = await getSessionPayload();

  if (!session?.organization_id) {
    redirect("/login");
  }

  try {
    const tree = await serverFetch<TreeNodeType[]>(
      `/organizations/${session.organization_id}/groups/tree`
    );

    return (
      <main className="space-y-6 p-6 md:p-8">
        <header className="space-y-2">
          <h1 className="text-2xl font-bold text-slate-900 md:text-3xl">Estructura organizacional</h1>
          <p className="max-w-3xl text-sm text-slate-600 md:text-base">
            Aquí puedes visualizar la jerarquía de grupos y subgrupos de tu organización.
          </p>
        </header>

        {tree.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-slate-600">
            No hay grupos definidos. Crea grupos desde la sección Grupos.
          </p>
        ) : (
          <section className="space-y-4">
            {tree.map((node) => (
              <TreeNode key={node.id} node={node} />
            ))}
          </section>
        )}
      </main>
    );
  } catch (error) {
    return (
      <main className="p-6 md:p-8">
        <p className="text-red-600">{error instanceof Error ? error.message : "Error inesperado"}</p>
      </main>
    );
  }
}
