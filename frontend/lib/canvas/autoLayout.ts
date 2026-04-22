// ============================================================
// Auto-layout — capa Estructura
// ============================================================
// Envuelve @dagrejs/dagre para computar posiciones óptimas de
// un grafo dirigido. La función es pura: no muta los inputs.
//
// Uso:
//   - Modo automático (silencioso): aplicar antes del primer
//     render cuando `nodesNeedAutoLayout()` detecta posiciones
//     default. No persiste.
//   - Modo explícito (botón): el usuario decide reordenar. El
//     caller persiste el resultado vía PATCH /nodes/positions.
//
// Dagre devuelve coordenadas del CENTRO del nodo; React Flow
// espera coordenadas del TOP-LEFT. La conversión ocurre aquí.

import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "reactflow";

export type AutoLayoutDirection = "TB" | "LR" | "BT" | "RL";

export interface AutoLayoutOptions {
  /** Dirección del rankdir: TB top-bottom, LR left-right, etc. Default "TB". */
  direction?: AutoLayoutDirection;
  /** Ancho estimado del nodo para el algoritmo de layout. Default 200. */
  nodeWidth?: number;
  /** Alto estimado del nodo para el algoritmo de layout. Default 80. */
  nodeHeight?: number;
  /** Separación entre niveles (eje principal del rankdir). Default 100. */
  rankSep?: number;
  /** Separación entre nodos del mismo nivel. Default 60. */
  nodeSep?: number;
  /** Padding horizontal del grafo completo. Default 40. */
  marginX?: number;
  /** Padding vertical del grafo completo. Default 40. */
  marginY?: number;
}

const DEFAULTS: Required<AutoLayoutOptions> = {
  direction: "TB",
  nodeWidth: 200,
  nodeHeight: 80,
  rankSep: 100,
  nodeSep: 60,
  marginX: 40,
  marginY: 40,
};

/**
 * Computa posiciones óptimas para un grafo de nodos usando dagre.
 * No muta los inputs.
 *
 * @returns Mapa `{ [nodeId]: { x, y } }` con coordenadas TOP-LEFT
 *          compatibles con React Flow. Si un node no está en el
 *          mapa (raro, sólo si dagre lo omite) el caller debe
 *          preservar su posición actual.
 */
export function computeAutoLayout(
  nodes: Node[],
  edges: Edge[],
  options?: AutoLayoutOptions,
): Record<string, { x: number; y: number }> {
  const opts = { ...DEFAULTS, ...(options ?? {}) };

  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: opts.direction,
    nodesep: opts.nodeSep,
    ranksep: opts.rankSep,
    marginx: opts.marginX,
    marginy: opts.marginY,
  });
  g.setDefaultEdgeLabel(() => ({}));

  for (const n of nodes) {
    g.setNode(n.id, { width: opts.nodeWidth, height: opts.nodeHeight });
  }

  const nodeIds = new Set(nodes.map((n) => n.id));
  for (const e of edges) {
    if (nodeIds.has(e.source) && nodeIds.has(e.target)) {
      g.setEdge(e.source, e.target);
    }
  }

  dagre.layout(g);

  const out: Record<string, { x: number; y: number }> = {};
  for (const n of nodes) {
    const laid = g.node(n.id);
    if (!laid) continue;
    // dagre → centro; react flow → top-left
    out[n.id] = {
      x: laid.x - opts.nodeWidth / 2,
      y: laid.y - opts.nodeHeight / 2,
    };
  }
  return out;
}

/**
 * Heurística: ¿los nodos están en posiciones default y necesitan
 * auto-layout inicial?
 *
 * Reglas:
 *  - Menos de 2 nodos → false (nada que acomodar).
 *  - Todos exactamente en (0, 0) → true.
 *  - Todos dentro de un radio de 50 px del origen → true (sugiere
 *    que nadie los movió nunca; auto-layout hace sentido).
 *  - En cualquier otro caso → false (ya hay layout manual;
 *    respetar).
 */
export function nodesNeedAutoLayout(nodes: Node[]): boolean {
  if (nodes.length < 2) return false;

  const allAtOrigin = nodes.every(
    (n) => n.position.x === 0 && n.position.y === 0,
  );
  if (allAtOrigin) return true;

  const radius = 50;
  const allNearOrigin = nodes.every(
    (n) =>
      Math.abs(n.position.x) <= radius && Math.abs(n.position.y) <= radius,
  );
  return allNearOrigin;
}
