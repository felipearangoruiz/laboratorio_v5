import Link from "next/link";
import { redirect } from "next/navigation";

import { getSessionPayload } from "../../lib/session";

const NAV_ITEMS = [
  { href: "/admin", label: "Resumen", hint: "Estado general del caso" },
  { href: "/groups", label: "Estructura", hint: "Grupos y organización" },
  { href: "/members", label: "Personas", hint: "Miembros e invitaciones" },
  { href: "/interviews", label: "Entrevistas", hint: "Seguimiento y respuestas" },
  { href: "/results", label: "Resultados", hint: "Diagnóstico disponible" },
];

export default async function AdminLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getSessionPayload();

  if (!session) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 gap-6 px-4 py-6 lg:grid-cols-[280px_minmax(0,1fr)] lg:px-6">
        <aside className="rounded-3xl bg-slate-900 p-6 text-slate-100 shadow-xl">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              Laboratorio
            </p>
            <h1 className="text-2xl font-semibold">Modelamiento institucional</h1>
            <p className="text-sm leading-6 text-slate-300">
              La operación del producto se organiza alrededor del avance del caso y del diagnóstico,
              no de entidades técnicas aisladas.
            </p>
          </div>

          <nav className="mt-8 space-y-3">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-3 transition hover:border-slate-700 hover:bg-slate-800"
              >
                <div className="font-medium">{item.label}</div>
                <div className="mt-1 text-sm text-slate-400">{item.hint}</div>
              </Link>
            ))}
          </nav>

          <div className="mt-8 rounded-2xl border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-300">
            <p>
              <span className="font-medium text-slate-100">Rol:</span> {session.role}
            </p>
            <p className="mt-2 break-all">
              <span className="font-medium text-slate-100">Organización:</span>{" "}
              {session.organization_id ?? "pendiente"}
            </p>
          </div>
        </aside>

        <main className="rounded-3xl bg-white shadow-sm">{children}</main>
      </div>
    </div>
  );
}
