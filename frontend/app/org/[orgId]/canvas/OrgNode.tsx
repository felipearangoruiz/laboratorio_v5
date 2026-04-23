"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { User, Users, Building2 } from "lucide-react";

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
  /** Sprint 5.B feature (i) — std heredado del bucket, viene de
   *  scores[dim].node_stds[nodeId]. El canvas lo usa para modular el
   *  grosor del borde (std bajo → 1px, std alto → 5px). null si no hay
   *  datos (run pre-5.A o nodo sin entrada). */
  tensionStd?: number | null;
  /** Sprint 5.B feature (iii) — nodo sin evidencia suficiente: no tiene
   *  entrada en scores del run. Se renderiza en gris con tooltip, sobre-
   *  escribiendo verde/amarillo/rojo. El grosor de borde se mantiene
   *  (feature i) si hay std heredado del bucket. */
  noEvidence?: boolean;
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
 * Sprint 5.B feature (i) — mapea std por nodo a grosor de borde.
 *
 * El spec habla de "std ≥ 1.5 → 5px" en la escala Likert cruda (0-5).
 * El motor normaliza scores a [0, 1] (ver _compute_node_scores del
 * backend), así que el std empírico en Meridian vive en ~[0, 0.35].
 * Usamos 0.5 como punto de saturación — con eso Meridian mapea a
 * grosores de ~1.7–3.5px, visible sin saturar. Si en el futuro el
 * motor expone scores en escala 0-5 crudo, ajustar STD_SATURATION a 1.5.
 */
const STD_EDGE_MIN_PX = 1;
const STD_EDGE_MAX_PX = 5;
const STD_SATURATION = 0.5;

function edgeWidthFromStd(std: number | null | undefined): number {
  if (std == null) return STD_EDGE_MIN_PX;
  const clamped = Math.min(Math.max(std, 0), STD_SATURATION);
  const t = clamped / STD_SATURATION;
  return STD_EDGE_MIN_PX + t * (STD_EDGE_MAX_PX - STD_EDGE_MIN_PX);
}

/**
 * Sprint 2.B Turno D — render minimalista para capa Estructura.
 * Nombre + icono de tipo + status dot según convención UX:
 *   Person: gris (none/pending) · amarillo (in_progress) · verde
 *   (completed) · gris punteado (expired).
 *   Unit:   sin dot (empty) · amarillo (incomplete) · verde (complete).
 *
 * Post-Sprint 2.B — distinción visual clara unit vs person:
 *   Person: cápsula blanca (rounded-full), borde 1px, ícono User en
 *     círculo.
 *   Unit:   caja gris (rounded-md), borde 2px, ícono Building2 en
 *     cuadrado acento.
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

  // Shape / surface difference per node type.
  const containerClass = isPerson
    ? // Person: cápsula blanca, borde 1px.
      selected
      ? "bg-white rounded-full border border-[#C2410C] shadow-[0_0_0_3px_rgba(194,65,12,0.15)] px-4 py-2"
      : "bg-white rounded-full border border-warm-300 hover:border-warm-400 px-4 py-2"
    : // Unit: caja gris suave, borde 2px, esquinas rectas.
      selected
      ? "bg-warm-100 rounded-md border-2 border-[#C2410C] shadow-[0_0_0_3px_rgba(194,65,12,0.15)] px-4 py-3"
      : "bg-warm-100 rounded-md border-2 border-warm-300 hover:border-warm-400 px-4 py-3";

  return (
    <div className={`relative ${isPerson ? "min-w-[170px]" : "min-w-[180px]"}`}>
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !bg-[#6b7280] !border-2 !border-[#0D0D14]"
      />
      <div
        className={`transition-all ${containerClass}`}
        style={{ boxShadow: "0 4px 16px rgba(0,0,0,0.18)" }}
      >
        <div className="flex items-center gap-2.5">
          <div className="flex-shrink-0">
            {isPerson ? (
              <div className="w-6 h-6 rounded-full bg-warm-100 flex items-center justify-center">
                <User className="w-3.5 h-3.5 text-warm-500" strokeWidth={1.75} />
              </div>
            ) : (
              <div className="w-8 h-8 rounded-md bg-accent/15 flex items-center justify-center">
                <Building2 className="w-4 h-4 text-accent" strokeWidth={1.75} />
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
  // Sprint 5.B feature (iii) — marca de nodo sin evidencia en capa Análisis.
  // Sobrescribe el color de tensión por gris neutro + tooltip. Se activa
  // cuando el enrich de page.tsx no encontró el nodo en diagnosis.scores.
  const noEvidence        = showAnalysis && data.noEvidence === true;
  const hasBadge          = showResultados && (data.findingCount ?? 0) > 0;
  const hasRing           = showResultados && data.isRingHighlighted === true;
  const opacity           = data.isHighlighted === false ? 0.35 : 1;

  // Sprint 5.B feature (i) — grosor de borde proporcional al std del nodo.
  // Solo aplica en capa Análisis; otras capas mantienen 1.5px / 2px.
  // Los nodos sin evidencia también tienen grosor dinámico si heredan std
  // de su bucket (node_stds ≠ null aunque node_scores sí lo sea).
  const dynamicBorderWidth = showAnalysis
    ? edgeWidthFromStd(data.tensionStd)
    : null;

  // Color del borde en capa Análisis: verde/amarillo/rojo cuando hay
  // tensión; gris neutro cuando está marcado como sin evidencia.
  const NO_EVIDENCE_COLOR = "#9CA3AF"; // neutral-400
  const dynamicBorderColor = noEvidence
    ? NO_EVIDENCE_COLOR
    : tc
    ? tc.hex
    : undefined;

  const borderClass = selected
    ? "border-[#C2410C] border-2 shadow-[0_0_0_3px_rgba(194,65,12,0.15)]"
    : hasTension || noEvidence
    ? ""  // borderWidth/borderColor inline (ver dynamicBorderWidth/Color)
    : showStatus && status !== "none"
    ? `${STATUS_BORDER[status]} border-[1.5px]`
    : "border-[#D4D0C8] border-[1.5px] hover:border-[#A8A29E]";

  const noEvidenceTooltip =
    "Sin evidencia suficiente: este nodo no tiene respondente activo, o su cobertura del instrumento es insuficiente.";

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
        className={`${noEvidence ? "bg-warm-50" : "bg-white"} rounded-[6px] px-4 py-3 transition-all ${borderClass}`}
        title={noEvidence ? noEvidenceTooltip : undefined}
        style={{
          boxShadow: "0 4px 16px rgba(0,0,0,0.18)",
          borderColor: dynamicBorderColor,
          borderStyle: dynamicBorderWidth !== null ? "solid" : undefined,
          borderWidth:
            dynamicBorderWidth !== null ? `${dynamicBorderWidth}px` : undefined,
          transition: "border-color 0.2s ease, border-width 0.2s ease",
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
          {hasTension && !noEvidence && tc && (
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${tc.dot}`} />
          )}

          {/* Sin evidencia — dot gris con tooltip (Sprint 5.B feature iii) */}
          {noEvidence && (
            <div
              className="w-2 h-2 rounded-full flex-shrink-0 bg-neutral-400"
              title={noEvidenceTooltip}
              aria-label={noEvidenceTooltip}
            />
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
