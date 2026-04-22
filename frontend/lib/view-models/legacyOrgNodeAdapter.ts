// ============================================================
// Sprint 2.B — legacyOrgNodeAdapter
// ============================================================
// Proyecta un Node + NodeState del nuevo modelo a la shape que
// OrgNode y las capas Análisis/Resultados esperan actualmente
// (heredada de la era Group/Member).
//
// Esta capa adapter permite refactorizar page.tsx al nuevo
// modelo sin romper los componentes legacy en los commits
// intermedios. Retirarla cuando OrgNode consuma Node/NodeState
// nativos (Turno D).

import type { Node, NodeState, NodeStateStatus } from "@/lib/types";

export type LegacyInterviewStatus =
  | "none"
  | "pending"
  | "in_progress"
  | "completed"
  | "expired";

export interface LegacyOrgNodeData {
  label: string;
  area: string;
  role: string;
  email: string;
  memberCount: number;
  level: number | null;
  nodeType: string;
  contextNotes: string;
  activeLayer: "estructura" | "analisis" | "resultados";
  interviewStatus: LegacyInterviewStatus;
  /**
   * Sprint 2.B Turno D — estado visual para units (áreas) en capa
   * Estructura. Lo setea el caller (page.tsx) usando computeAreaStatus;
   * el adapter no lo calcula porque requiere conocer child persons.
   */
  unitStatus?: "empty" | "incomplete" | "complete";
}

/**
 * Mapea un NodeStateStatus (nuevo modelo) al LegacyInterviewStatus
 * que OrgNode consume. Preferimos NodeState si está disponible; si
 * no, caemos a `attrs.token_status` (heredado del Member legacy).
 *
 * Correspondencia lossy (por decisión de Sprint 2.B):
 *   invited      → pending
 *   in_progress  → in_progress
 *   completed    → completed
 *   skipped      → expired
 */
export function mapNodeStateToLegacyStatus(
  nodeStateStatus: NodeStateStatus | undefined,
  attrsTokenStatus: unknown,
): LegacyInterviewStatus {
  if (nodeStateStatus) {
    switch (nodeStateStatus) {
      case "invited":
        return "pending";
      case "in_progress":
        return "in_progress";
      case "completed":
        return "completed";
      case "skipped":
        return "expired";
    }
  }
  if (typeof attrsTokenStatus === "string") {
    const legacy = attrsTokenStatus as LegacyInterviewStatus;
    if (["pending", "in_progress", "completed", "expired"].includes(legacy)) {
      return legacy;
    }
  }
  return "none";
}

export function toLegacyOrgNodeData(
  node: Node,
  nodeState: NodeState | undefined,
  memberCount: number,
  activeLayer: "estructura" | "analisis" | "resultados",
): LegacyOrgNodeData {
  const attrs = (node.attrs ?? {}) as Record<string, unknown>;
  return {
    label: node.name,
    area: (attrs.area as string) ?? "",
    role: (attrs.tarea_general as string) ?? "",
    email: (attrs.email as string) ?? "",
    memberCount,
    level: (attrs.nivel_jerarquico as number | null) ?? null,
    // Map el nuevo `type` ("unit"|"person") al legacy ("area"|"person")
    // que OrgNode y SidePanel esperan. `attrs.node_type_legacy` tiene
    // precedencia si existe (sub-tipos legacy como "direccion", etc.).
    nodeType:
      (attrs.node_type_legacy as string) ??
      (node.type === "unit" ? "area" : "person"),
    contextNotes: (attrs.context_notes as string) ?? "",
    activeLayer,
    interviewStatus: mapNodeStateToLegacyStatus(
      nodeState?.status,
      attrs.token_status,
    ),
  };
}
