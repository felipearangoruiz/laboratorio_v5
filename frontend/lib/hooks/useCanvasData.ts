"use client";

// ============================================================
// Sprint 2.2 — useCanvasData() hook unificado
// ============================================================
// Encapsula las 3 queries del nuevo modelo que el canvas
// necesita de forma conjunta:
//   - listNodes(orgId)
//   - listEdges(orgId)
//   - listNodeStates({ campaign_id? })
//
// Refetchea automáticamente cuando cambia `orgId` (provisto
// por `useOrg()`) o `campaignId`.
//
// Opciones:
//   - campaignId?: filtra node_states por campaña
//   - includeDeleted?: default false. Excluye nodes con
//     `deleted_at != null` (soft-delete).

import { useCallback, useEffect, useState } from "react";
import { listNodes, listEdges, listNodeStates } from "@/lib/api";
import { useOrg } from "@/lib/contexts/OrgContext";
import type { Node, Edge, NodeState } from "@/lib/types";

export interface UseCanvasDataOptions {
  campaignId?: string;
  includeDeleted?: boolean;
}

export interface UseCanvasDataResult {
  nodes: Node[];
  edges: Edge[];
  nodeStates: NodeState[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useCanvasData(
  options: UseCanvasDataOptions = {},
): UseCanvasDataResult {
  const { orgId } = useOrg();
  const { campaignId, includeDeleted = false } = options;

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [nodeStates, setNodeStates] = useState<NodeState[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    if (!orgId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [rawNodes, rawEdges, rawStates] = await Promise.all([
        listNodes(orgId),
        listEdges(orgId),
        listNodeStates(campaignId ? { campaign_id: campaignId } : undefined),
      ]);
      const filteredNodes = includeDeleted
        ? rawNodes
        : rawNodes.filter((n) => n.deleted_at === null);
      const filteredEdges = includeDeleted
        ? rawEdges
        : rawEdges.filter((e) => e.deleted_at === null);
      setNodes(filteredNodes);
      setEdges(filteredEdges);
      setNodeStates(rawStates);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Error cargando datos del canvas",
      );
    } finally {
      setIsLoading(false);
    }
  }, [orgId, campaignId, includeDeleted]);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  return {
    nodes,
    edges,
    nodeStates,
    isLoading,
    error,
    refetch: fetchAll,
  };
}
