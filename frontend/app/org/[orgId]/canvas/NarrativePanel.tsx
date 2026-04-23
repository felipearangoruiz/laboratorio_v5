"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  X,
  FileDown,
  TrendingUp,
  TrendingDown,
  Lightbulb,
  CheckCircle2,
  Minus,
  AlertCircle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import type { DiagnosisResult, DiagnosisFinding } from "@/lib/api";

interface Props {
  diagnosis: DiagnosisResult;
  onClose: () => void;
  /** Hard highlight: closes panel and switches layer to highlight nodes */
  onHighlightNodes: (nodeIds: string[]) => void;
  /** Soft highlight: highlights nodes in canvas without closing panel */
  onSoftHighlightNodes?: (nodeIds: string[]) => void;
  /** Sprint 5.C feature (iii) — deep-link: si se pasa un findingId, el
   *  panel hace scroll automático al finding y lo expande al montarse. */
  targetFindingId?: string | null;
  /** Sprint 5.C feature (v) — mapa id → nombre del nodo para renderizar
   *  chips legibles en narrative_sections.dimensions[*].node_ids. */
  nodeNames?: Record<string, string>;
  /** Sprint 5.C feature (vi) — clic en chip de nodo: cierra panel y
   *  selecciona el nodo (capa Resultados abre su panel lateral). */
  onNodeClick?: (nodeId: string) => void;
  /** Sprint 5.C feature (vi) — clic en header de dimensión: switch a
   *  capa Análisis y aplica esa dim como filtro. */
  onDimensionClick?: (dimension: string) => void;
}

const DIM_LABELS: Record<string, string> = {
  liderazgo:       "Liderazgo",
  comunicacion:    "Comunicación",
  cultura:         "Cultura",
  procesos:        "Procesos",
  poder:           "Poder",
  economia:        "Economía",
  operacion:       "Operación",
  mision:          "Misión",
  centralizacion:  "Centralización",
  cuellos_botella: "Cuellos de botella",
  alineacion:      "Alineación",
  bienestar:       "Bienestar",
  recursos:        "Recursos",
  vision:          "Visión",
};

function dimLabel(key: string): string {
  return DIM_LABELS[key.toLowerCase()] ?? key;
}

/** Normalize confidence from string or float to "high"|"medium"|"low" */
function normalizeConfidence(c: string | number): "high" | "medium" | "low" {
  if (typeof c === "number") {
    if (c >= 0.7) return "high";
    if (c >= 0.45) return "medium";
    return "low";
  }
  const lower = c.toLowerCase();
  if (lower === "high" || lower === "alta") return "high";
  if (lower === "low" || lower === "baja") return "low";
  return "medium";
}

/** Get the best dimension label for a finding (supports both formats) */
function findingDimLabel(f: DiagnosisFinding): string {
  if (f.dimensions && f.dimensions.length > 0) return dimLabel(f.dimensions[0]);
  if (f.dimension) return dimLabel(f.dimension);
  return "";
}

// ── Confidence badge ──────────────────────────────────────────────
function ConfidenceBadge({ confidence }: { confidence: string | number }) {
  const norm = normalizeConfidence(confidence);
  const map: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    high:   { label: "Alta",  cls: "bg-green-50 text-green-700 border-green-200",  icon: <CheckCircle2 className="w-3 h-3" /> },
    medium: { label: "Media", cls: "bg-amber-50 text-amber-700 border-amber-200",  icon: <Minus className="w-3 h-3" /> },
    low:    { label: "Baja",  cls: "bg-red-50 text-red-700 border-red-200",        icon: <AlertCircle className="w-3 h-3" /> },
  };
  const c = map[norm];
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${c.cls}`}>
      {c.icon}{c.label}
    </span>
  );
}

// ── Simple markdown renderer ──────────────────────────────────────
// Handles: ## headings, **bold**, *italic*, - bullet lists, blank lines
function SimpleMarkdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let listBuffer: string[] = [];

  function flushList() {
    if (listBuffer.length === 0) return;
    elements.push(
      <ul key={`ul-${elements.length}`} className="list-disc list-inside space-y-1 text-sm text-warm-700 leading-relaxed mb-3">
        {listBuffer.map((item, i) => (
          <li key={i}>{renderInline(item)}</li>
        ))}
      </ul>
    );
    listBuffer = [];
  }

  function renderInline(s: string): React.ReactNode {
    // Bold + italic combined
    const parts = s.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} className="font-semibold text-warm-900">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("*") && part.endsWith("*")) {
        return <em key={i}>{part.slice(1, -1)}</em>;
      }
      return part;
    });
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith("## ")) {
      flushList();
      elements.push(
        <h3 key={i} className="text-sm font-semibold text-warm-900 mt-5 mb-2 first:mt-0">
          {line.slice(3)}
        </h3>
      );
    } else if (line.startsWith("# ")) {
      flushList();
      elements.push(
        <h2 key={i} className="text-base font-bold text-warm-900 mt-6 mb-3 first:mt-0">
          {line.slice(2)}
        </h2>
      );
    } else if (line.startsWith("### ")) {
      flushList();
      elements.push(
        <h4 key={i} className="text-xs font-semibold text-warm-700 uppercase tracking-wide mt-4 mb-1.5 first:mt-0">
          {line.slice(4)}
        </h4>
      );
    } else if (/^[-*] /.test(line)) {
      listBuffer.push(line.slice(2));
    } else if (line.trim() === "") {
      flushList();
      // blank line — visual spacer handled by parent spacing
    } else {
      flushList();
      elements.push(
        <p key={i} className="text-sm text-warm-700 leading-relaxed mb-2">
          {renderInline(line)}
        </p>
      );
    }
  }
  flushList();
  return <>{elements}</>;
}

// ── Main panel ────────────────────────────────────────────────────
export default function NarrativePanel({
  diagnosis,
  onClose,
  onHighlightNodes,
  onSoftHighlightNodes,
  targetFindingId,
  nodeNames,
  onNodeClick,
  onDimensionClick,
}: Props) {
  const [expandedFinding, setExpandedFinding] = useState<string | null>(
    targetFindingId ?? null,
  );
  const findingRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const observerRef = useRef<IntersectionObserver | null>(null);
  // Sprint 5.C feature (vi) — observer auxiliar para dimension cards
  // del narrative_sections. Al entrar en viewport, dispara soft-highlight
  // sobre los node_ids de la dim.
  const dimRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const dimObserverRef = useRef<IntersectionObserver | null>(null);

  // Sprint 5.C feature (iii) — deep-link scroll + expand al finding.
  // Cada vez que cambia targetFindingId (el usuario abrió el panel desde
  // el CTA "Ver en diagnóstico" de otro finding), expandimos ese id y
  // scrolleamos su tarjeta a vista. Requiere un rAF porque las refs
  // pueden no estar pobladas en el mismo tick del montaje.
  useEffect(() => {
    if (!targetFindingId) return;
    setExpandedFinding(targetFindingId);
    const raf = requestAnimationFrame(() => {
      const el = findingRefs.current.get(targetFindingId);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
    return () => cancelAnimationFrame(raf);
  }, [targetFindingId]);

  // Escape key to close
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // IntersectionObserver: soft-highlight nodes when finding scrolls into view
  const setupObserver = useCallback(() => {
    if (!onSoftHighlightNodes) return;
    observerRef.current?.disconnect();

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const findingId = (entry.target as HTMLElement).dataset.findingId;
            if (!findingId) continue;
            const finding = findings.find((f) => f.id === findingId);
            if (finding?.node_ids?.length) {
              onSoftHighlightNodes(finding.node_ids);
            }
          }
        }
      },
      { threshold: 0.6 }
    );

    findingRefs.current.forEach((el) => {
      if (el) observerRef.current?.observe(el);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onSoftHighlightNodes]);

  useEffect(() => {
    setupObserver();
    return () => observerRef.current?.disconnect();
  }, [setupObserver]);

  // Sprint 5.C feature (vi) — IntersectionObserver sobre dimension cards.
  // Se configura aparte para evitar mezclar selectores y thresholds.
  const setupDimObserver = useCallback(() => {
    if (!onSoftHighlightNodes) return;
    dimObserverRef.current?.disconnect();

    dimObserverRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const raw = (entry.target as HTMLElement).dataset.nodeIds;
            if (!raw) continue;
            const ids = raw.split(",").filter(Boolean);
            if (ids.length > 0) onSoftHighlightNodes(ids);
          }
        }
      },
      { threshold: 0.5 },
    );
    dimRefs.current.forEach((el) => {
      if (el) dimObserverRef.current?.observe(el);
    });
  }, [onSoftHighlightNodes]);

  useEffect(() => {
    setupDimObserver();
    return () => dimObserverRef.current?.disconnect();
  }, [setupDimObserver]);

  // Clear soft highlight when panel unmounts
  useEffect(() => {
    return () => {
      onSoftHighlightNodes?.([]);
    };
  }, [onSoftHighlightNodes]);

  const scoreEntries    = Object.entries(diagnosis.scores || {});
  const findings        = diagnosis.findings || [];
  const recommendations = diagnosis.recommendations || [];
  const hasNarrative    = diagnosis.narrative_md && diagnosis.narrative_md.trim().length > 0;
  const sections        = diagnosis.narrative_sections || null;

  /** Helper: nombre amigable del nodo; fallback a los primeros 8
   *  caracteres del UUID si el mapa no lo tiene (run huérfano o nodo
   *  ya eliminado). */
  const nodeLabel = (nid: string): string =>
    nodeNames?.[nid] ?? nid.slice(0, 8);

  /** Sprint 5.C feature (vi) — chip de nodo interactivo. Hover dispara
   *  soft-highlight (pulse en canvas). Click cierra panel y abre el
   *  panel lateral del nodo (capa Resultados). Si no hay callbacks,
   *  renderiza un span no-interactivo (fallback defensivo). */
  const renderNodeChip = (nid: string) => {
    const label = nodeLabel(nid);
    const canClick = typeof onNodeClick === "function";
    const canHover = typeof onSoftHighlightNodes === "function";
    if (!canClick && !canHover) {
      return (
        <span
          key={nid}
          className="px-2 py-0.5 bg-warm-100 text-warm-700 text-[10px] rounded-full font-medium"
          title={nid}
        >
          {label}
        </span>
      );
    }
    return (
      <button
        key={nid}
        type="button"
        onClick={() => canClick && onNodeClick!(nid)}
        onMouseEnter={() => canHover && onSoftHighlightNodes!([nid])}
        onMouseLeave={() => canHover && onSoftHighlightNodes!([])}
        onFocus={() => canHover && onSoftHighlightNodes!([nid])}
        onBlur={() => canHover && onSoftHighlightNodes!([])}
        className="px-2 py-0.5 bg-warm-100 hover:bg-accent/15 focus:bg-accent/15 text-warm-700 hover:text-accent focus:text-accent text-[10px] rounded-full font-medium transition-colors cursor-pointer focus:outline-none"
        title={`Ver ${label} en el canvas`}
      >
        {label}
      </button>
    );
  };

  const overallScore =
    scoreEntries.length > 0
      ? scoreEntries.reduce((sum, [, d]) => sum + (d.score ?? 0), 0) / scoreEntries.length
      : 0;

  function handleFindingNodeClick(f: DiagnosisFinding) {
    if (f.node_ids?.length > 0) {
      onHighlightNodes(f.node_ids);
    }
  }

  function setFindingRef(el: HTMLDivElement | null, findingId: string) {
    if (el) {
      findingRefs.current.set(findingId, el);
      observerRef.current?.observe(el);
    } else {
      findingRefs.current.delete(findingId);
    }
  }

  return (
    <div
      className="absolute top-0 right-0 h-full bg-warm-50 border-l border-warm-200 shadow-warm-md z-30 flex flex-col"
      style={{ width: "clamp(420px, 65%, 860px)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-warm-200 bg-white flex-shrink-0">
        <div>
          <h2 className="font-display italic text-xl text-warm-900">Diagnóstico Organizacional</h2>
          <p className="text-xs text-warm-500 mt-0.5">
            {findings.length} hallazgos · {recommendations.length} recomendaciones
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-warm-300 rounded-md hover:bg-warm-100 text-warm-600 transition-colors">
            <FileDown className="w-3.5 h-3.5" />
            Exportar PDF
          </button>
          <button onClick={onClose} className="text-warm-400 hover:text-warm-700 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-8">

        {/* Score global */}
        {overallScore > 0 && (
          <div className="text-center p-5 bg-white rounded-xl border border-warm-200">
            <p className="text-xs font-semibold text-warm-400 uppercase tracking-widest mb-1">
              Score Global
            </p>
            <p className="text-5xl font-bold text-warm-900 tabular-nums">
              {overallScore.toFixed(1)}
              <span className="text-xl text-warm-400 font-normal">/5</span>
            </p>
            <p className="text-xs text-warm-400 mt-1">
              {overallScore >= 3.8 ? "Saludable" : overallScore >= 2.5 ? "Atención recomendada" : "Intervención urgente"}
            </p>
          </div>
        )}

        {/* Scores por dimensión */}
        {scoreEntries.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-warm-900 mb-3">Scores por Dimensión</h3>
            <div className="space-y-2.5">
              {scoreEntries.map(([dim, data]) => {
                const score  = data.score ?? 0;
                const pct    = Math.round(Math.min(100, Math.max(0, score * 20)));
                const avgPct = data.avg !== undefined
                  ? Math.round(Math.min(100, Math.max(0, data.avg * 20)))
                  : undefined;
                const barColor =
                  score >= 3.8 ? "bg-emerald-500" : score >= 2.5 ? "bg-amber-500" : "bg-red-500";

                return (
                  <div key={dim} className="flex items-center gap-3">
                    <span className="text-sm text-warm-700 w-28 truncate capitalize">{dimLabel(dim)}</span>
                    <div className="flex-1 h-2 bg-warm-100 rounded-full overflow-hidden relative">
                      <div
                        className={`h-full rounded-full transition-all ${barColor}`}
                        style={{ width: `${pct}%` }}
                      />
                      {avgPct !== undefined && (
                        <div
                          className="absolute top-0 bottom-0 w-px bg-warm-400/60"
                          style={{ left: `${avgPct}%` }}
                          title={`Promedio org: ${data.avg?.toFixed(1)}`}
                        />
                      )}
                    </div>
                    <span className="text-sm font-semibold text-warm-900 w-8 text-right tabular-nums">
                      {score.toFixed(1)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Sprint 5.C feature (v) — narrativa estructurada cuando el
            motor la provee (runs post-5.A). Fallback al narrative_md
            monolítico para runs antiguos. */}
        {sections ? (
          <>
            {/* a. Executive summary */}
            {sections.executive_summary.markdown.trim() && (
              <section>
                <h3 className="text-sm font-semibold text-warm-900 mb-3">Resumen Ejecutivo</h3>
                <div className="bg-white border border-warm-200 rounded-lg px-5 py-4">
                  <SimpleMarkdown text={sections.executive_summary.markdown} />
                </div>
              </section>
            )}

            {/* b. Análisis por dimensión — una card por entrada */}
            {sections.dimensions.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-warm-900 mb-3">Análisis por dimensión</h3>
                <div className="space-y-3">
                  {sections.dimensions.map((d) => {
                    const scorePct = Math.round(Math.min(100, Math.max(0, d.score * 100)));
                    const barColor =
                      d.score >= 0.5 ? "bg-emerald-500" : d.score >= 0.25 ? "bg-amber-500" : "bg-red-500";
                    const canClickDim = typeof onDimensionClick === "function";
                    return (
                      <div
                        key={d.dimension}
                        ref={(el) => {
                          if (el) {
                            dimRefs.current.set(d.dimension, el);
                            dimObserverRef.current?.observe(el);
                          } else {
                            dimRefs.current.delete(d.dimension);
                          }
                        }}
                        data-node-ids={d.node_ids.join(",")}
                        className="bg-white border border-warm-200 rounded-lg px-5 py-4"
                      >
                        <div className="flex items-center justify-between mb-2">
                          {canClickDim ? (
                            <button
                              type="button"
                              onClick={() => onDimensionClick!(d.dimension)}
                              className="text-sm font-semibold text-warm-900 capitalize hover:text-accent focus:text-accent focus:outline-none transition-colors text-left truncate"
                              title={`Ver ${dimLabel(d.dimension)} en capa Análisis`}
                            >
                              {dimLabel(d.dimension)}
                            </button>
                          ) : (
                            <h4 className="text-sm font-semibold text-warm-900 capitalize">
                              {dimLabel(d.dimension)}
                            </h4>
                          )}
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="text-[10px] text-warm-500 tabular-nums">
                              std {d.std.toFixed(2)}
                            </span>
                            <span className="text-[11px] font-semibold text-warm-900 tabular-nums">
                              {d.score.toFixed(2)}
                            </span>
                          </div>
                        </div>
                        <div className="h-1.5 bg-warm-100 rounded-full overflow-hidden mb-3">
                          <div
                            className={`h-full rounded-full transition-all ${barColor}`}
                            style={{ width: `${scorePct}%` }}
                          />
                        </div>
                        <SimpleMarkdown text={d.markdown} />
                        {d.node_ids.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-warm-100">
                            <span className="text-[10px] text-warm-400 mr-1">
                              Nodos afectados:
                            </span>
                            {d.node_ids.map((nid) => renderNodeChip(nid))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* c. Hallazgos transversales */}
            {sections.transversal_findings.markdown.trim() && (
              <section>
                <h3 className="text-sm font-semibold text-warm-900 mb-3">Hallazgos transversales</h3>
                <div className="bg-white border border-warm-200 rounded-lg px-5 py-4">
                  <SimpleMarkdown text={sections.transversal_findings.markdown} />
                  {sections.transversal_findings.node_ids.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-warm-100">
                      <span className="text-[10px] text-warm-400 mr-1">Involucrados:</span>
                      {sections.transversal_findings.node_ids.map((nid) => renderNodeChip(nid))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* d. Resumen de recomendaciones */}
            {sections.recommendations_summary.markdown.trim() && (
              <section>
                <h3 className="text-sm font-semibold text-warm-900 mb-3">Resumen de recomendaciones</h3>
                <div className="bg-white border border-warm-200 rounded-lg px-5 py-4">
                  <SimpleMarkdown text={sections.recommendations_summary.markdown} />
                </div>
              </section>
            )}

            {/* e. Advertencias */}
            {sections.warnings.markdown.trim() && (
              <section>
                <h3 className="text-sm font-semibold text-warm-900 mb-3 flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-amber-500" />
                  Advertencias metodológicas
                </h3>
                <div className="bg-amber-50/50 border border-amber-200 rounded-lg px-5 py-4">
                  <SimpleMarkdown text={sections.warnings.markdown} />
                </div>
              </section>
            )}
          </>
        ) : (
          /* Fallback legacy — narrative_md monolítico (runs pre-5.A) */
          hasNarrative && (
            <div>
              <h3 className="text-sm font-semibold text-warm-900 mb-3">Resumen Ejecutivo</h3>
              <div className="bg-white border border-warm-200 rounded-lg px-5 py-4">
                <SimpleMarkdown text={diagnosis.narrative_md} />
              </div>
            </div>
          )
        )}

        {/* Hallazgos */}
        {findings.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-warm-900 mb-1">Hallazgos</h3>
            <p className="text-xs text-warm-400 mb-3">
              Usa "Ver en el mapa →" para resaltar los nodos relacionados en el canvas.
            </p>
            <div className="space-y-2">
              {findings.map((f) => {
                const isOpen     = expandedFinding === f.id;
                const isStrength = f.type === "strength" || f.type === "fortaleza";
                const hasNodes   = f.node_ids?.length > 0;
                const dimStr     = findingDimLabel(f);

                return (
                  <div
                    key={f.id}
                    ref={(el) => setFindingRef(el, f.id)}
                    data-finding-id={f.id}
                    className="border border-warm-200 rounded-lg overflow-hidden bg-white"
                  >
                    <div className="flex items-stretch">
                      <button
                        onClick={() => setExpandedFinding(isOpen ? null : f.id)}
                        className="flex-1 flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-warm-50 transition-colors min-w-0"
                      >
                        {isStrength ? (
                          <TrendingUp className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-warm-900 leading-snug">{f.title}</p>
                          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                            {dimStr && (
                              <span className="text-[10px] text-warm-400 capitalize">{dimStr}</span>
                            )}
                            <ConfidenceBadge confidence={f.confidence} />
                            {hasNodes && (
                              <span className="text-[10px] text-warm-400">
                                {f.node_ids.length} nodo{f.node_ids.length !== 1 ? "s" : ""}
                              </span>
                            )}
                          </div>
                        </div>
                        {isOpen
                          ? <ChevronDown className="w-4 h-4 text-warm-400 flex-shrink-0 mt-0.5" />
                          : <ChevronRight className="w-4 h-4 text-warm-400 flex-shrink-0 mt-0.5" />}
                      </button>

                      {hasNodes && (
                        <button
                          onClick={() => handleFindingNodeClick(f)}
                          className="flex-shrink-0 flex items-center px-3 text-[11px] font-semibold text-accent hover:text-accent/70 hover:bg-warm-50 border-l border-warm-100 transition-colors whitespace-nowrap"
                          title={`Ver ${f.node_ids.length} nodo${f.node_ids.length !== 1 ? "s" : ""} en el canvas`}
                        >
                          Ver en el mapa →
                        </button>
                      )}
                    </div>

                    {isOpen && (
                      <div className="px-4 pb-3 pt-2 border-t border-warm-100">
                        <p className="text-sm text-warm-700 leading-relaxed">{f.description}</p>
                        {f.confidence_rationale && (
                          <p className="text-[11px] text-warm-400 mt-2 italic">{f.confidence_rationale}</p>
                        )}
                        {/* All dimensions (new motor) */}
                        {f.dimensions && f.dimensions.length > 1 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {f.dimensions.map((d, i) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.5 bg-warm-100 text-warm-600 text-[10px] rounded capitalize"
                              >
                                {dimLabel(d)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Recomendaciones */}
        {recommendations.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-warm-900 mb-3 flex items-center gap-1.5">
              <Lightbulb className="w-4 h-4 text-accent" />
              Recomendaciones
            </h3>
            <div className="space-y-2.5">
              {[...recommendations]
                .sort((a, b) => (a.priority ?? 99) - (b.priority ?? 99))
                .map((r, i) => (
                  <div key={r.id ?? i} className="p-3 border border-warm-200 rounded-lg bg-white">
                    <div className="flex items-start gap-2">
                      <span className="text-xs font-bold text-accent bg-accent/10 rounded w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">
                        {r.priority ?? i + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-warm-900">{r.title}</p>
                        <p className="text-sm text-warm-600 mt-0.5 leading-relaxed">{r.description}</p>
                        {/* Horizon / impact / effort metadata */}
                        {(r.horizon || r.impact || r.effort) && (
                          <div className="flex items-center gap-3 mt-2 text-[10px] text-warm-400">
                            {r.horizon && (
                              <span>Horizonte: <span className="font-medium text-warm-600 capitalize">{r.horizon}</span></span>
                            )}
                            {r.impact && (
                              <span>Impacto: <span className="font-medium text-warm-600 capitalize">{r.impact}</span></span>
                            )}
                            {r.effort && (
                              <span>Esfuerzo: <span className="font-medium text-warm-600 capitalize">{r.effort}</span></span>
                            )}
                          </div>
                        )}
                        {r.node_ids?.length > 0 && (
                          <p className="text-[10px] text-warm-400 mt-1.5">
                            Aplica a {r.node_ids.length} nodo{r.node_ids.length !== 1 ? "s" : ""}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Metadata */}
        <div className="text-xs text-warm-400 border-t border-warm-200 pt-4">
          {diagnosis.completed_at && (
            <p>
              Generado el{" "}
              {new Date(diagnosis.completed_at).toLocaleDateString("es-ES", {
                day:   "numeric",
                month: "long",
                year:  "numeric",
              })}
            </p>
          )}
          <p className="mt-1">Presiona <kbd className="px-1 py-0.5 bg-warm-100 rounded text-warm-500">Esc</kbd> para cerrar</p>
        </div>
      </div>
    </div>
  );
}
