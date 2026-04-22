"use client";

// ============================================================
// Sprint 2.2 — OrgContext + useOrg()
// ============================================================
// Provider que expone el `orgId` y la `Organization` cargada
// al árbol de componentes dentro de `/org/[orgId]/...`.
//
// Objetivo: preparar el terreno para eliminar el prop drilling
// de `orgId` (y re-fetches duplicados de organization) en
// Sprint 2.3. En Sprint 2.2 NO se migran componentes; el
// provider solo envuelve el layout y la prop sigue viva.
//
// Uso:
//   const { orgId, organization, isLoading, error } = useOrg();

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useParams } from "next/navigation";
import { getOrganization } from "@/lib/api";
import type { Organization } from "@/lib/types";

interface OrgContextValue {
  orgId: string;
  organization: Organization | null;
  isLoading: boolean;
  error: string | null;
}

const OrgContext = createContext<OrgContextValue | null>(null);

interface OrgProviderProps {
  /** orgId explícito. Si se omite, se extrae de useParams(). */
  orgId?: string;
  children: ReactNode;
}

export function OrgProvider({ orgId: orgIdProp, children }: OrgProviderProps) {
  const params = useParams();
  const orgIdFromParams =
    typeof params?.orgId === "string" ? params.orgId : "";
  const orgId = orgIdProp ?? orgIdFromParams;

  const [organization, setOrganization] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(Boolean(orgId));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orgId) {
      setOrganization(null);
      setIsLoading(false);
      setError(null);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    getOrganization(orgId)
      .then((org) => {
        if (!cancelled) {
          setOrganization(org);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Error cargando organización");
          setIsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  const value = useMemo<OrgContextValue>(
    () => ({ orgId, organization, isLoading, error }),
    [orgId, organization, isLoading, error],
  );

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>;
}

/**
 * Hook de consumo del OrgContext. Lanza si se llama fuera de
 * un OrgProvider — ayuda a detectar integraciones incorrectas
 * antes de que se propaguen a runtime.
 */
export function useOrg(): OrgContextValue {
  const ctx = useContext(OrgContext);
  if (!ctx) {
    throw new Error(
      "useOrg() debe usarse dentro de un <OrgProvider>. " +
        "Revisa que el layout /org/[orgId]/layout.tsx envuelva el árbol.",
    );
  }
  return ctx;
}
