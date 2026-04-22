"use client";

// ============================================================
// Sprint 2.2 — layout de /org/[orgId]/*
// ============================================================
// Envuelve todas las páginas bajo /org/[orgId]/ con
// <OrgProvider>, exponiendo el orgId y la Organization a los
// descendientes vía `useOrg()`.
//
// NOTA: no se elimina el prop drilling de `orgId` en los
// componentes descendientes en Sprint 2.2; eso ocurre en
// Sprint 2.3. Este layout es aditivo.

import type { ReactNode } from "react";
import { OrgProvider } from "@/lib/contexts/OrgContext";

export default function OrgLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: { orgId: string };
}) {
  return <OrgProvider orgId={params.orgId}>{children}</OrgProvider>;
}
