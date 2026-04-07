import Link from "next/link";
import { redirect } from "next/navigation";
import { getSessionPayload } from "../../lib/session";

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
    <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", minHeight: "100vh" }}>
      <aside
        style={{
          borderRight: "1px solid #ddd",
          padding: "1.5rem",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <nav>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: "0.75rem" }}>
            <li><Link href="/admin">/admin</Link></li>
            <li><Link href="/admin/organizacion">/admin/organizacion</Link></li>
            <li><Link href="/admin/grupos">/admin/grupos</Link></li>
            <li><Link href="/admin/miembros">/admin/miembros</Link></li>
            <li><Link href="/admin/entrevistas">/admin/entrevistas</Link></li>
            <li><Link href="/admin/procesamiento">/admin/procesamiento</Link></li>
            <li><Link href="/admin/diagnostico">/admin/diagnostico</Link></li>
          </ul>
        </nav>

        <div>
          <p>role: {session.role}</p>
          <p>user_id: {session.user_id}</p>
        </div>
      </aside>

      <main style={{ padding: "1.5rem" }}>{children}</main>
    </div>
  );
}
