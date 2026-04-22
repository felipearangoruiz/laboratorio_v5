"use client";

// ============================================================
// Sprint 2.B — useActiveCampaign()
// ============================================================
// Obtiene la campaña 'active' única de una organización.
// Aprovecha el invariante #11 de Sprint 2.1: como máximo una
// campaña activa por org a la vez.
//
// Uso:
//   const { campaign, isLoading, error } = useActiveCampaign(orgId);
//
// Si no hay campaña activa, `campaign` es null (y se emite un
// console.warn una sola vez por montaje del hook).

import { useEffect, useRef, useState } from "react";
import { listCampaigns } from "@/lib/api";
import type { AssessmentCampaign } from "@/lib/types";

export interface UseActiveCampaignResult {
  campaign: AssessmentCampaign | null;
  isLoading: boolean;
  error: string | null;
}

export function useActiveCampaign(orgId: string | null | undefined): UseActiveCampaignResult {
  const [campaign, setCampaign] = useState<AssessmentCampaign | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const warnedRef = useRef(false);

  useEffect(() => {
    if (!orgId) {
      setCampaign(null);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    listCampaigns(orgId)
      .then((campaigns) => {
        if (cancelled) return;
        const active = campaigns.find((c) => c.status === "active") ?? null;
        setCampaign(active);
        if (!active && !warnedRef.current) {
          warnedRef.current = true;
          // eslint-disable-next-line no-console
          console.warn("No active campaign for org", orgId);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Error cargando campañas",
        );
        setCampaign(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orgId]);

  return { campaign, isLoading, error };
}
