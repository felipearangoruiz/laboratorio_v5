// ============================================================
// Sprint 2.2 — View-models para React Flow
// ============================================================
// Aísla el shape que vive en backend (Node/Edge/NodeState) del
// shape que consume React Flow. Evita que los componentes
// tengan que conocer detalles internos del backend
// (`attrs: Record<string, unknown>`, `deleted_at`, etc.).
//
// Política: los componentes del canvas NO deberían consumir
// Node/Edge crudos; deben consumir CanvasNode/CanvasEdge. Las
// funciones `toCanvasNode` / `toCanvasEdge` son los únicos
// traductores permitidos.

import type {
  Node,
  Edge,
  NodeState,
  NodeType,
  NodeStateStatus,
  EdgeType,
} from "@/lib/types";

export interface CanvasNode {
  id: string;
  type: "unit" | "person";
  position: { x: number; y: number };
  data: {
    label: string;
    nodeType: NodeType;
    attrs: Record<string, unknown>;
    stateStatus?: NodeStateStatus;
    respondedAt?: string;
    memberCount?: number;
  };
}

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  data: {
    edgeType: EdgeType;
    edgeMetadata: Record<string, unknown>;
  };
}

/**
 * Proyecta un Node (+ NodeState opcional) al shape que React
 * Flow espera en <ReactFlow nodes={...} />.
 */
export function toCanvasNode(
  node: Node,
  nodeState?: NodeState,
  memberCount?: number,
): CanvasNode {
  return {
    id: node.id,
    type: node.type,
    position: { x: node.position_x, y: node.position_y },
    data: {
      label: node.name,
      nodeType: node.type,
      attrs: node.attrs ?? {},
      stateStatus: nodeState?.status,
      respondedAt: nodeState?.completed_at ?? undefined,
      memberCount,
    },
  };
}

/**
 * Proyecta un Edge al shape que React Flow espera en
 * <ReactFlow edges={...} />.
 */
export function toCanvasEdge(edge: Edge): CanvasEdge {
  return {
    id: edge.id,
    source: edge.source_node_id,
    target: edge.target_node_id,
    data: {
      edgeType: edge.edge_type,
      edgeMetadata: edge.edge_metadata ?? {},
    },
  };
}
