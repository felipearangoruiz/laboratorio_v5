"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  MarkerType,
  Panel,
} from "reactflow";
import "reactflow/dist/style.css";

import {
  createGroup,
  updateGroup,
  deleteGroup,
  updatePositions,
  getCollectionStatus,
  getLatestDiagnosis,
  getAnalysisStatus,
  updateOrganization,
  type DiagnosisResult,
  type AnalysisRunStatus,
} from "@/lib/api";
import DocumentsOverlay from "./DocumentsOverlay";
import { useAuth } from "@/hooks/useAuth";
import OrgNode from "./OrgNode";
import PersonPanel from "./PersonPanel";
import UnitPanel from "./UnitPanel";
import AnalysisLayer from "./AnalysisLayer";
import AnalysisNodePanel from "./AnalysisNodePanel";
import DimensionFilter from "./DimensionFilter";
import NarrativePanel from "./NarrativePanel";
import ResultsNodePanel from "./ResultsNodePanel";
import DiagnosisGate from "./DiagnosisGate";
import Sidebar from "./Sidebar";
import EmptyState from "./EmptyState";
import LayerSelector from "./LayerSelector";
import { Loader2, Plus, User, Users } from "lucide-react";
import { useCanvasData } from "@/lib/hooks/useCanvasData";
import { useActiveCampaign } from "@/lib/hooks/useActiveCampaign";
import { useOrg } from "@/lib/contexts/OrgContext";
import { toLegacyOrgNodeData } from "@/lib/view-models/legacyOrgNodeAdapter";
import { computeAreaStatus } from "@/lib/view-models/areaStatus";
import type { Node as ModelNode } from "@/lib/types";

const nodeTypes = { orgNode: OrgNode };

// ── Tension helpers ───────────────────────────────────────────────
/**
 * Convert a 0–5 score to a 0–100 tension value.
 * High tension = problem. Low tension = healthy.
 * If dimension is specified, uses node_scores for that dimension.
 * If null, averages tension across all dimensions.
 */
function computeNodeTension(
  nodeId: string,
  scores: DiagnosisResult["scores"],
  dimension: string | null,
): number | undefined {
  if (!scores || Object.keys(scores).length === 0) return undefined;

  if (dimension) {
    const s = scores[dimension]?.node_scores?.[nodeId];
    if (s === undefined) return undefined;
    return Math.round((1 - Math.min(s, 5) / 5) * 100);
  }

  const tensionValues = Object.values(scores)
    .map((d) => {
      const s = d.node_scores?.[nodeId];
      if (s === undefined) return null;
      return Math.round((1 - Math.min(s, 5) / 5) * 100);
    })
    .filter((t): t is number => t !== null);

  if (tensionValues.length === 0) return undefined;
  return Math.round(tensionValues.reduce((a, b) => a + b, 0) / tensionValues.length);
}

type StructureType = "people" | "areas" | "mixed";

type LegacyLayer = "estructura" | "analisis" | "resultados";

/**
 * Sprint 2.B: proyección de Node[] del nuevo modelo al formato
 * ReactFlow, enriquecido con NodeState (capa Estructura) y con
 * edges jerárquicas generadas desde `parent_node_id`.
 */
function buildFlowFromModel(
  modelNodes: ModelNode[],
  nodeStates: import("@/lib/types").NodeState[],
  modelEdges: import("@/lib/types").Edge[],
  activeCampaignId: string | null,
  activeLayer: LegacyLayer,
): { nodes: Node[]; edges: Edge[] } {
  // Memberships por unit (para memberCount).
  const childCountByUnit: Record<string, number> = {};
  for (const n of modelNodes) {
    if (n.type === "person" && n.parent_node_id) {
      childCountByUnit[n.parent_node_id] =
        (childCountByUnit[n.parent_node_id] ?? 0) + 1;
    }
  }

  const flowNodes: Node[] = modelNodes.map((n) => {
    const state = nodeStates.find(
      (ns) =>
        ns.node_id === n.id &&
        (!activeCampaignId || ns.campaign_id === activeCampaignId),
    );
    const memberCount =
      n.type === "unit" ? childCountByUnit[n.id] ?? 0 : 0;
    const data = toLegacyOrgNodeData(n, state, memberCount, activeLayer);
    if (n.type === "unit") {
      const childPersons = modelNodes.filter(
        (c) => c.parent_node_id === n.id && c.type === "person",
      );
      const areaStatus = computeAreaStatus(
        n,
        childPersons,
        nodeStates,
        activeCampaignId,
      );
      data.unitStatus = areaStatus.label;
    }
    return {
      id: n.id,
      type: "orgNode",
      position: { x: n.position_x, y: n.position_y },
      data,
    };
  });

  // Edges jerárquicas (parent_node_id) + edges explícitas (lateral/process).
  const hierarchical: Edge[] = modelNodes
    .filter((n) => n.parent_node_id)
    .map((n) => ({
      id: `e-tree-${n.parent_node_id}-${n.id}`,
      source: n.parent_node_id!,
      target: n.id,
      type: "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#94a3b8", strokeWidth: 2 },
    }));

  const explicit: Edge[] = modelEdges.map((e) => ({
    id: `e-${e.edge_type}-${e.id}`,
    source: e.source_node_id,
    target: e.target_node_id,
    type: "smoothstep",
    style: {
      stroke: e.edge_type === "lateral" ? "#64748b" : "#94a3b8",
      strokeWidth: 2,
      strokeDasharray: e.edge_type === "lateral" ? "4 4" : undefined,
    },
  }));

  return { nodes: flowNodes, edges: [...hierarchical, ...explicit] };
}

export default function CanvasPage() {
  const { loading: authLoading } = useAuth();
  const { orgId, organization } = useOrg();

  // Sprint 2.B: useCanvasData es la única fuente de verdad de
  // Node/Edge/NodeState. useActiveCampaign aprovecha el invariante
  // 11 (máximo una campaña 'active' por org).
  const {
    nodes: modelNodes,
    edges: modelEdges,
    nodeStates,
    isLoading: canvasLoading,
    refetch: refetchCanvas,
  } = useCanvasData();
  const { campaign: activeCampaign } = useActiveCampaign(orgId);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeLayer, setActiveLayer] = useState<LegacyLayer>("estructura");
  const [thresholdMet, setThresholdMet] = useState(false);
  const [diagnosis, setDiagnosis] = useState<DiagnosisResult | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisRunStatus | null>(null);
  const [structureType, setStructureType] = useState<StructureType>("areas");
  const [showNodeTypeSelector, setShowNodeTypeSelector] = useState(false);
  const [showDocuments, setShowDocuments] = useState(false);
  // Legacy nodeStatuses (Record<id,string>) derivado del nuevo NodeState
  // para mantener compat con DiagnosisGate y otros consumidores.
  const nodeStatuses = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const ns of nodeStates) {
      if (activeCampaign && ns.campaign_id !== activeCampaign.id) continue;
      map[ns.node_id] = ns.status;
    }
    return map;
  }, [nodeStates, activeCampaign]);
  // Analysis layer state
  const [activeDimension,   setActiveDimension]   = useState<string | null>(null);
  const [showNarrative,     setShowNarrative]     = useState(false);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string> | null>(null);
  const dragTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isEmpty = !canvasLoading && modelNodes.length === 0;

  // ── Per-node finding counts (for resultados badges) ───────────────
  const nodeFindingCounts = useMemo<Record<string, number>>(() => {
    if (!diagnosis?.findings) return {};
    const counts: Record<string, number> = {};
    for (const f of diagnosis.findings) {
      for (const nodeId of f.node_ids || []) {
        counts[nodeId] = (counts[nodeId] || 0) + 1;
      }
    }
    return counts;
  }, [diagnosis]);

  const nodeTopFinding = useMemo<Record<string, string>>(() => {
    if (!diagnosis?.findings) return {};
    const tops: Record<string, string> = {};
    for (const f of diagnosis.findings) {
      for (const nodeId of f.node_ids || []) {
        if (!tops[nodeId]) tops[nodeId] = f.title; // first = highest priority
      }
    }
    return tops;
  }, [diagnosis]);

  // Load org structure type desde OrgContext (evita re-fetch).
  useEffect(() => {
    if (organization?.org_structure_type) {
      setStructureType(organization.org_structure_type as StructureType);
    }
  }, [organization]);

  const loadMeta = useCallback(async () => {
    if (!orgId) return;
    try {
      const [collStatus, diag, runStatus] = await Promise.allSettled([
        getCollectionStatus(orgId),
        getLatestDiagnosis(orgId),
        getAnalysisStatus(orgId),
      ]);
      if (collStatus.status === "fulfilled") {
        setThresholdMet(collStatus.value.threshold_met);
        // nodeStatuses ahora se deriva de useCanvasData().nodeStates.
      }
      if (diag.status === "fulfilled" && diag.value && diag.value.status === "ready") {
        setDiagnosis(diag.value);
      }
      if (runStatus.status === "fulfilled") {
        setAnalysisStatus(runStatus.value);
      }
    } catch { /* ignore */ }
  }, [orgId]);

  useEffect(() => { loadMeta(); }, [loadMeta]);

  // Re-render ReactFlow cuando cambian Node/Edge/NodeState/capa/campaña.
  useEffect(() => {
    if (modelNodes.length > 0) {
      const { nodes: n, edges: e } = buildFlowFromModel(
        modelNodes,
        nodeStates,
        modelEdges,
        activeCampaign?.id ?? null,
        activeLayer,
      );

      if (activeLayer === "analisis" && diagnosis?.status === "ready") {
        // Enrich with tension scores + highlighting for análisis layer
        const enriched = n.map((node) => {
          const tension = computeNodeTension(node.id, diagnosis.scores, activeDimension);
          let isHighlighted: boolean | undefined = undefined;

          if (highlightedNodeIds !== null) {
            isHighlighted = highlightedNodeIds.has(node.id);
          } else if (activeDimension !== null && tension !== undefined) {
            isHighlighted = tension > 40;
          }

          return {
            ...node,
            data: { ...node.data, tensionScore: tension, isHighlighted },
          };
        });
        setNodes(enriched);

      } else if (activeLayer === "resultados" && diagnosis?.status === "ready") {
        // Enrich with finding badges + ring highlighting for resultados layer
        const enriched = n.map((node) => {
          const fc           = nodeFindingCounts[node.id] ?? 0;
          const topTitle     = nodeTopFinding[node.id];
          let isHighlighted: boolean | undefined  = undefined;
          let isRingHighlighted: boolean | undefined = undefined;

          if (highlightedNodeIds !== null) {
            const inSet       = highlightedNodeIds.has(node.id);
            isHighlighted     = inSet;
            isRingHighlighted = inSet;
          }

          return {
            ...node,
            data: {
              ...node.data,
              findingCount:    fc,
              topFindingTitle: topTitle,
              isHighlighted,
              isRingHighlighted,
            },
          };
        });
        setNodes(enriched);

      } else {
        setNodes(n);
      }
      setEdges(e);
    } else {
      setNodes([]);
      setEdges([]);
    }
  }, [
    modelNodes, modelEdges, nodeStates, activeCampaign,
    activeLayer, diagnosis,
    activeDimension, highlightedNodeIds,
    nodeFindingCounts, nodeTopFinding,
    setNodes, setEdges,
  ]);

  const onConnect = useCallback(
    async (connection: Connection) => {
      if (!connection.source || !connection.target) return;
      await updateGroup(connection.target, {
        parent_group_id: connection.source,
      });
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            type: "smoothstep",
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: "#94a3b8", strokeWidth: 2 },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  const onNodeDragStop = useCallback(
    (_: any, node: Node) => {
      if (dragTimerRef.current) clearTimeout(dragTimerRef.current);
      dragTimerRef.current = setTimeout(() => {
        updatePositions(orgId, [
          {
            id: node.id,
            position_x: node.position.x,
            position_y: node.position.y,
          },
        ]);
      }, 500);
    },
    [orgId]
  );

  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNode(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setShowNodeTypeSelector(false);
    setHighlightedNodeIds(null); // Clear any finding-based highlighting
  }, []);

  /** Called from NarrativePanel triggered by análisis layer — switches to análisis. */
  const handleHighlightNodes = useCallback((nodeIds: string[]) => {
    setHighlightedNodeIds(new Set(nodeIds));
    setShowNarrative(false);
    setActiveLayer("analisis");
  }, []);

  /** Called from NarrativePanel triggered by resultados layer — stays in resultados. */
  const handleHighlightNodesInMap = useCallback((nodeIds: string[]) => {
    setHighlightedNodeIds(new Set(nodeIds));
    setShowNarrative(false);
    // Layer stays as "resultados" — ring animation on relevant nodes
  }, []);

  /**
   * Soft highlight — called by IntersectionObserver in NarrativePanel as the
   * user scrolls through findings. Does NOT close the panel or change layer.
   * Clears itself when nodeIds is empty.
   */
  const handleSoftHighlightNodes = useCallback((nodeIds: string[]) => {
    setHighlightedNodeIds(nodeIds.length > 0 ? new Set(nodeIds) : null);
  }, []);

  /**
   * Navega desde capa Análisis a capa Resultados preservando el nodo
   * seleccionado (spec: ARQUITECTURA_ANALISIS_RESULTADOS.md §3).
   */
  const navigateToResultsWithNode = useCallback((nodeId: string) => {
    setActiveLayer("resultados");
    setSelectedNode(nodeId);
    setShowNarrative(false);
    setHighlightedNodeIds(null);
  }, []);

  async function handleStructureTypeSelected(type: StructureType) {
    setStructureType(type);
    await updateOrganization(orgId, { org_structure_type: type });
  }

  async function handleAddNode(nodeType?: "person" | "area") {
    // Determine node type based on structure setting
    let resolvedType: "person" | "area";
    if (nodeType) {
      resolvedType = nodeType;
    } else if (structureType === "people") {
      resolvedType = "person";
    } else if (structureType === "areas") {
      resolvedType = "area";
    } else {
      // Mixed mode — show selector
      setShowNodeTypeSelector(true);
      return;
    }

    await createNodeOfType(resolvedType);
  }

  async function createNodeOfType(nodeType: "person" | "area") {
    setShowNodeTypeSelector(false);
    const defaultName = nodeType === "person" ? "Nueva persona" : "Nueva área";
    const newNode = await createGroup({
      organization_id: orgId,
      node_type: nodeType,
      name: defaultName,
      position_x: Math.random() * 400 + 100,
      position_y: Math.random() * 300 + 100,
    });
    await refetchCanvas();
    setSelectedNode(newNode.id);
  }

  async function handleDeleteNode(nodeId: string) {
    try {
      await deleteGroup(nodeId);
    } catch (err: any) {
      alert(err?.message || "No se pudo eliminar el nodo");
      return;
    }
    setSelectedNode(null);
    await refetchCanvas();
  }

  async function handleTemplateApplied() {
    await refetchCanvas();
  }

  if (authLoading || canvasLoading) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: "#0D0D14" }}>
        <div className="w-8 h-8 border-2 border-white/10 border-t-white/60 rounded-full animate-spin" />
      </div>
    );
  }

  const selectedNodeData = selectedNode
    ? nodes.find((n) => n.id === selectedNode)
    : null;

  // Sprint 2.B: resolver el Node raw (modelo nuevo) y su NodeState
  // para los paneles nuevos (PersonPanel / UnitPanel).
  const selectedModelNode = selectedNode
    ? modelNodes.find((n) => n.id === selectedNode) ?? null
    : null;
  const selectedNodeState = selectedModelNode
    ? nodeStates.find(
        (ns) =>
          ns.node_id === selectedModelNode.id &&
          (!activeCampaign || ns.campaign_id === activeCampaign.id),
      )
    : undefined;

  return (
    <div className="h-screen flex overflow-hidden" style={{ background: "#0D0D14" }}>
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        orgId={orgId}
        onDocumentsClick={() => setShowDocuments(true)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <LayerSelector
          active={activeLayer}
          onChange={(layer) => setActiveLayer(layer as LegacyLayer)}
          hasNodes={nodes.length > 0}
          thresholdMet={thresholdMet}
          hasDiagnosis={!!diagnosis}
        />

        {/* Sprint 2.B: indicador compacto de progreso en la capa Estructura.
            Reemplaza la barra CollectionProgress del tab eliminado. */}
        {activeLayer === "estructura" && !isEmpty && (() => {
          const personNodes = modelNodes.filter((n) => n.type === "person");
          const total = personNodes.length;
          const completed = personNodes.filter((p) =>
            nodeStates.some(
              (ns) =>
                ns.node_id === p.id &&
                ns.status === "completed" &&
                (!activeCampaign || ns.campaign_id === activeCampaign.id),
            ),
          ).length;
          if (total === 0) return null;
          return (
            <div
              className="h-8 flex items-center px-4 text-[11px] text-white/50 border-b"
              style={{
                background: "rgba(13,13,20,0.6)",
                borderBottomColor: "rgba(255,255,255,0.06)",
              }}
            >
              {completed} de {total} miembros respondieron
            </div>
          );
        })()}

        {/* Dimension filter — análisis layer with ready diagnosis */}
        {activeLayer === "analisis" && diagnosis?.status === "ready" && (
          <DimensionFilter
            diagnosis={diagnosis}
            active={activeDimension}
            onChange={(dim) => {
              setActiveDimension(dim);
              setHighlightedNodeIds(null);
            }}
          />
        )}

        <div className="flex-1 relative">
          {isEmpty ? (
            <EmptyState
              orgId={orgId}
              onStructureTypeSelected={handleStructureTypeSelected}
              onCreateNode={(nodeType) => handleAddNode(nodeType)}
              onTemplateApplied={handleTemplateApplied}
              onCsvImported={handleTemplateApplied}
            />
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              style={{ background: "#0D0D14" }}
              onConnect={activeLayer === "estructura" ? onConnect : undefined}
              onNodeDragStop={onNodeDragStop}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.3 }}
              deleteKeyCode={null}
              proOptions={{ hideAttribution: true }}
              nodesDraggable={true}
              connectOnClick={activeLayer === "estructura"}
            >
              <Background color="#1a1a2a" gap={28} />
              <Controls showInteractive={false} />
            </ReactFlow>
          )}

          {/* Floating add button — always visible in estructura layer */}
          {!isEmpty && activeLayer === "estructura" && (
            <div className="absolute bottom-6 right-6 z-20">
              <div className="relative">
                {showNodeTypeSelector && (
                  <div className="absolute bottom-14 right-0 rounded-lg border border-white/10 bg-[#1a1a2a] py-2 w-48 shadow-canvas">
                    <button
                      onClick={() => createNodeOfType("person")}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/6 text-left transition-colors"
                    >
                      <User className="w-4 h-4 text-white/50" strokeWidth={1.5} />
                      <span className="text-sm text-white/70">Persona</span>
                    </button>
                    <button
                      onClick={() => createNodeOfType("area")}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/6 text-left transition-colors"
                    >
                      <Users className="w-4 h-4 text-white/50" strokeWidth={1.5} />
                      <span className="text-sm text-white/70">Área</span>
                    </button>
                  </div>
                )}
                <button
                  onClick={() => handleAddNode()}
                  className="w-12 h-12 bg-accent text-white rounded-full flex items-center justify-center hover:bg-accent-hover transition-all hover:scale-105 active:scale-95"
                  style={{ boxShadow: "0 4px 20px rgba(194,65,12,0.45)" }}
                  title="Agregar nodo"
                >
                  <Plus className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}

          {/* Side panel — capa Estructura usa paneles nuevos (Sprint 2.B).
              PersonPanel y UnitPanel reemplazan a SidePanel+CollectionPanel
              legacy. SidePanel/CollectionPanel/CollectionProgress quedan en
              código pero desreferenciados; Turno D los mueve a legacy/. */}
          {selectedModelNode && activeLayer === "estructura" && selectedModelNode.type === "person" && (
            <PersonPanel
              node={selectedModelNode}
              nodeState={selectedNodeState}
              orgId={orgId}
              onClose={() => setSelectedNode(null)}
              onDelete={handleDeleteNode}
              onRefetch={refetchCanvas}
            />
          )}
          {selectedModelNode && activeLayer === "estructura" && selectedModelNode.type === "unit" && (
            <UnitPanel
              node={selectedModelNode}
              childPersons={modelNodes.filter(
                (n) => n.parent_node_id === selectedModelNode.id && n.type === "person",
              )}
              nodeStates={nodeStates}
              activeCampaignId={activeCampaign?.id ?? null}
              orgId={orgId}
              onClose={() => setSelectedNode(null)}
              onSelectNode={setSelectedNode}
              onDelete={handleDeleteNode}
              onRefetch={refetchCanvas}
            />
          )}

          {/* Sprint 2.B: se elimina el tab Recolección. La lógica de
              recolección se fusiona dentro de la capa Estructura en el
              Turno B (PersonPanel reemplaza a SidePanel/CollectionPanel). */}

          {/* Analysis layer — no diagnosis, no run: show verify-data prompt */}
          {activeLayer === "analisis" && !diagnosis &&
            analysisStatus?.status !== "running" && analysisStatus?.status !== "pending" && (
            <AnalysisLayer
              orgId={orgId}
              onDiagnosisGenerated={() => {
                loadMeta();
                setActiveLayer("resultados");
              }}
            />
          )}

          {/* Analysis layer — script running externally */}
          {activeLayer === "analisis" && !diagnosis &&
            (analysisStatus?.status === "running" || analysisStatus?.status === "pending") && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-50/80 backdrop-blur-sm z-5">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-gray-500 mx-auto mb-3" />
                <p className="text-sm font-medium text-gray-700">Análisis en progreso…</p>
                <p className="text-xs text-gray-400 mt-1">
                  El script externo está procesando los datos. Esto puede tardar unos minutos.
                </p>
                <button
                  onClick={loadMeta}
                  className="mt-4 text-xs text-gray-500 underline hover:text-gray-700"
                >
                  Actualizar estado
                </button>
              </div>
            </div>
          )}

          {/* Analysis layer — ready: node panel on click */}
          {selectedNodeData && activeLayer === "analisis" && diagnosis?.status === "ready" && (
            <AnalysisNodePanel
              orgId={orgId}
              nodeId={selectedNode!}
              nodeName={selectedNodeData.data.label}
              diagnosis={diagnosis}
              onClose={() => setSelectedNode(null)}
              onNavigateToResults={navigateToResultsWithNode}
            />
          )}

          {/* Resultados layer — no diagnosis yet: show progress gate */}
          {activeLayer === "resultados" && !diagnosis && (
            <DiagnosisGate
              orgId={orgId}
              completedNodes={Object.values(nodeStatuses).filter((s) => s === "completed").length}
              totalNodes={nodes.length}
              thresholdMet={thresholdMet}
              onInitiated={() => {
                loadMeta();
              }}
            />
          )}

          {/* Resultados layer — diagnosis ready: node panel on click */}
          {selectedNodeData && activeLayer === "resultados" && diagnosis?.status === "ready" && (
            <ResultsNodePanel
              nodeId={selectedNode!}
              nodeName={selectedNodeData.data.label}
              diagnosis={diagnosis}
              onClose={() => setSelectedNode(null)}
              onViewNarrative={() => setShowNarrative(true)}
            />
          )}

          {/* Narrative panel — full-width diagnosis view.
              Triggered from resultados layer (onHighlightNodes stays in resultados)
              or from análisis layer via showNarrative (onHighlightNodes switches to análisis). */}
          {(activeLayer === "resultados" || showNarrative) && diagnosis && (
            <NarrativePanel
              diagnosis={diagnosis}
              onClose={() => {
                if (showNarrative) {
                  setShowNarrative(false);
                } else {
                  setActiveLayer("estructura");
                }
                setHighlightedNodeIds(null);
              }}
              onHighlightNodes={
                showNarrative ? handleHighlightNodes : handleHighlightNodesInMap
              }
              onSoftHighlightNodes={handleSoftHighlightNodes}
            />
          )}
        </div>
      </div>

      {/* Documents overlay */}
      {showDocuments && (
        <DocumentsOverlay
          orgId={orgId}
          onClose={() => setShowDocuments(false)}
        />
      )}
    </div>
  );
}
