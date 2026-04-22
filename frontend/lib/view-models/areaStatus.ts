// ============================================================
// Sprint 2.B — computeAreaStatus()
// ============================================================
// Función pura que calcula el estado visual de un unit (área)
// en la capa Estructura del canvas:
//   - 'empty'      : sin miembros y sin descripción.
//   - 'incomplete' : tiene miembros pero no todos respondieron,
//                    o tiene descripción sin miembros.
//   - 'complete'   : tiene miembros y todos respondieron
//                    (filtrando por la campaña activa si aplica).

import type { Node, NodeState } from "@/lib/types";

export interface AreaStatus {
  label: "empty" | "incomplete" | "complete";
  completed: number;
  total: number;
}

export function computeAreaStatus(
  unit: Node,
  childPersons: Node[],
  nodeStates: NodeState[],
  activeCampaignId: string | null,
): AreaStatus {
  const relevantStates = activeCampaignId
    ? nodeStates.filter((ns) => ns.campaign_id === activeCampaignId)
    : nodeStates;

  const total = childPersons.length;
  const completed = childPersons.filter((p) =>
    relevantStates.some(
      (ns) => ns.node_id === p.id && ns.status === "completed",
    ),
  ).length;

  const attrs = (unit.attrs ?? {}) as Record<string, unknown>;
  const rawDescription = attrs.description;
  const hasDescription =
    typeof rawDescription === "string" && rawDescription.trim().length > 0;

  let label: AreaStatus["label"];
  if (total === 0 && !hasDescription) {
    label = "empty";
  } else if (total > 0 && completed === total) {
    label = "complete";
  } else {
    label = "incomplete";
  }

  return { label, completed, total };
}
