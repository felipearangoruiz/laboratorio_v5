"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { User, Users } from "lucide-react";

export interface OrgNodeData {
  label: string;
  area: string;
  role: string;
  email: string;
  memberCount: number;
  level: number | null;
  nodeType: "person" | "area";
  contextNotes?: string | null;
  interviewStatus?: "none" | "invited" | "in_progress" | "completed" | "expired" | "pending";
  activeLayer?: string;
  // Sprint 2.B — estado de unidad (área) en capa Estructura
  unitStatus?: "empty" | "incomplete" | "complete";
  // Análisis layer
  tensionScore?: number;    // 0–100 (100 = max tension)
  isHighlighted?: boolean;  // false → 0.35 opacity; undefined/true → full opacity
  // Resultados layer
  findingCount?: number;    // total findings for this node
  topFindingTitle?: string; // tooltip text for the badge
  isRingHighlighted?: boolean; // true → animated accent ring (bidirectional nav)
}

// Dot color for interview status (shown only in recoleccion layer)
const STATUS_DOT: Record<string, string> = {
  pending:     "bg-blue-400",
  invited:     "bg-blue-400",
  in_progress: "bg-blue-500 animate-pulse",
  completed:   "bg-emerald-500",
  expired:     "bg-orange-400",
};

const STATUS_BORDER: Record<string, string> = {
  pending:     "border-blue-300",
  invited:     "border-blue-300 border-dashed",
  in_progress: "border-blue-400",
  completed:   "border-emerald-400",
  expired:     "border-orange-300",
};

// Tension colors: 0–40 healthy, 41–70 caution, 71–100 critical
function tensionColor(score: number): { hex: string; dot: string } {
  if (score <= 40) return { hex: "#15803D", dot: "bg-emerald-600" };
  if (score <= 70) return { hex: "#B45309", dot: "bg-amber-600" };
  return { hex: "#DC2626", dot: "bg-red-600" };
}

/**
 * Sprint 2.B Turno D — render minimalista para capa Estructura.
 * Nombre + icono de tipo + status dot según convención UX:
 *   Person: gris (none/pending) · amarillo (in_progress) · verde
 *   (completed) · gris punteado (expired).
 *   Unit:   sin dot (empty) · amarillo (incomplete) · verde (complete).
 */
function OrgNodeStructureView({ data, selected }: NodeProps<OrgNodeData>) {
  const isPerson = data.nodeType === "person";
  const status = data.interviewStatus || "none";

  let dotClass: string | null = null;
  if (isPerson) {
    if (status === "in_progress") dotClass = "bg-yellow-500";
    else if (status === "completed") dotClass = "bg-green-500";
    else if (status === "expired")
      dotClass = "bg-gray-200 border border-dashed border-gray-400";
    else if (status === "pending" || status === "invited" || status === "none")
      dotClass = "bg-gray-400";
  } else {
    // Unit
    const unitStatus = data.unitStatus ?? "empty";
    if (unitStatus === "incomplete") dotClass = "bg-yellow-500";
    else if (unitStatus === "complete") dotClass = "bg-green-500";
    // empty → null (no dot)
  }

  const borderClass = selected
    ? "border-[#C2410C] border-2 shadow-[0_0_0_3px_rgba(194,65,12,0.15)]"
    : "border-[#D4D0C8] border-[1.5px] hover:border-[#A8A29E]";

  return (
    <div className="relative min-w-[160px]">
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !bg-[#6b7280] !border-2 !border-[#0D0D14]"
      />
      <div
        className={`bg-white rounded-[6px] px-4 py-3 transition-all ${borderClass}`}
        style={{ boxShadow: "0 4px 16px rgba(0,0,0,0.18)" }}
      >
        <div className="flex items-center gap-2.5">
          <div className="flex-shrink-0">
            {isPerson ? (
              <div className="w-7 h-7 rounded-full bg-warm-100 flex items-center justify-center">
                <User className="w-3.5 h-3.5 text-warm-500" strokeWidth={1.5} />
              </div>
            ) : (
              <div className="w-7 h-7 rounded-md bg-accent/10 flex items-center justify-center">
                <Users className="w-3.5 h-3.5 text-accent" strokeWidth={1.5} />
              </div>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-warm-900 truncate leading-tight">
              {data.label}
            </div>
          </div>
          {dotClass && (
            <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${dotClass}`} />
          )}
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2.5 !h-2.5 !bg-[#6b7280] !border-2 !border-[#0D0D14]"
      />
    </div>
  );
}

function OrgNode(props: NodeProps<OrgNodeData>) {
  if (props.data.activeLayer === "estructura") {
    return <OrgNodeStructureView {...props} />;
  }
  return <OrgNodeAnalysisResultsView {...props} />;
}

function OrgNodeAnalysisResultsView({ data, selected }: NodeProps<OrgNodeData>) {
  const showStatus    = data.activeLayer === "recoleccion";
  const showAnalysis  = data.activeLayer === "analisis";
  const showResultados = data.activeLayer === "resultados";
  const status        = data.interviewStatus || "none";
  const isPerson      = data.nodeType === "person";

  const hasTension        = showAnalysis && data.tensionScore !== undefined;
  const tc                = hasTension ? tensionColor(data.tensionScore!) : null;
  const hasBadge          = showResultados && (data.findingCount ?? 0) > 0;
  const hasRing           = showResultados && data.isRingHighlighted === true;
  const opacity           = data.isHighlighted === false ? 0.35 : 1;

  const borderClass = selected
    ? "border-[#C2410C] border-2 shadow-[0_0_0_3px_rgba(194,65,12,0.15)]"
    : hasTension
    ? "border-[1.5px]"
    : showStatus && status !== "none"
    ? `${STATUS_BORDER[status]} border-[1.5px]`
    : "border-[#D4D0C8] border-[1.5px] hover:border-[#A8A29E]";

  return (
    <div
      className="relative min-w-[160px]"
      style={{ opacity, transition: "opacity 0.2s ease" }}
    >
      {/* Animated ring for bidirectional finding navigation */}
      {hasRing && (
        <div
          className="absolute pointer-events-none animate-ping rounded-[8px]"
          style={{
            inset: "-3px",
            border: "2px solid #C2410C",
            borderRadius: "8px",
          }}
        />
      )}

      {/* Finding count badge (top-right corner) */}
      {hasBadge && (
        <div
          className="absolute -top-2 -right-2 z-10 flex items-center justify-center rounded-full pointer-events-none"
          style={{
            width: "18px",
            height: "18px",
            background: "#C2410C",
          }}
          title={data.topFindingTitle}
        >
          <span className="text-[9px] font-bold text-white leading-none">
            {data.findingCount! > 9 ? "9+" : data.findingCount}
          </span>
        </div>
      )}

      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !bg-[#6b7280] !border-2 !border-[#0D0D14]"
      />

      <div
        className={`bg-white rounded-[6px] px-4 py-3 transition-all ${borderClass}`}
        style={{
          boxShadow: "0 4px 16px rgba(0,0,0,0.18)",
          borderColor: tc ? tc.hex : undefined,
          transition: "border-color 0.2s ease",
        }}
      >
        <div className="flex items-center gap-2.5">
          {/* Icon */}
          <div className="flex-shrink-0">
            {isPerson ? (
              <div className="w-7 h-7 rounded-full bg-warm-100 flex items-center justify-center">
                <User className="w-3.5 h-3.5 text-warm-500" strokeWidth={1.5} />
              </div>
            ) : (
              <div className="w-7 h-7 rounded-md bg-accent/10 flex items-center justify-center">
                <Users className="w-3.5 h-3.5 text-accent" strokeWidth={1.5} />
              </div>
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-warm-900 truncate leading-tight">
              {data.label}
            </div>
            {isPerson && data.role && (
              <div className="text-[11px] text-warm-500 truncate mt-0.5 leading-tight">
                {data.role}
              </div>
            )}
          </div>

          {/* Tension dot — análisis layer */}
          {hasTension && tc && (
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${tc.dot}`} />
          )}

          {/* Status dot — recoleccion layer */}
          {!hasTension && showStatus && status !== "none" && (
            <div
              className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[status] ?? "bg-warm-400"}`}
            />
          )}
        </div>

        {/* Area badge */}
        {!isPerson && data.area && (
          <div className="mt-2">
            <span className="inline-block px-2 py-0.5 text-[10px] font-medium bg-accent/8 text-accent rounded-full">
              {data.area}
            </span>
          </div>
        )}

        {/* Member count pill */}
        {!isPerson && data.memberCount > 0 && (
          <div className="mt-1.5 flex items-center gap-1">
            <span className="text-[10px] text-warm-400">
              {data.memberCount} miembro{data.memberCount !== 1 ? "s" : ""}
            </span>
          </div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2.5 !h-2.5 !bg-[#6b7280] !border-2 !border-[#0D0D14]"
      />
    </div>
  );
}

export default memo(OrgNode);
