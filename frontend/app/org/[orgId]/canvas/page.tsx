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
  getOrgGroups,
  createGroup,
  updateGroup,
  deleteGroup,
  updatePositions,
  getCollectionStatus,
  getLatestDiagnosis,
  getOrganization,
  updateOrganization,
  type DiagnosisResult,
} from "@/lib/api";
import DocumentsOverlay from "./DocumentsOverlay";
import { useAuth } from "@/hooks/useAuth";
import OrgNode from "./OrgNode";
import SidePanel from "./SidePanel";
import CollectionPanel from "./CollectionPanel";
import CollectionProgress from "./CollectionProgress";
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

interface GroupData {
  id: string;
  name: string;
  description: string;
  node_type: string;
  email: string;
  area: string;
  tarea_general: string;
  context_notes: string | null;
  nivel_jerarquico: number | null;
  position_x: number;
  position_y: number;
  parent_group_id: string | null;
  organization_id: string;
  member_count: number;
  children: GroupData[];
}

function flattenTree(nodes: GroupData[]): GroupData[] {
  const result: GroupData[] = [];
  function walk(list: GroupData[]) {
    for (const n of list) {
      result.push(n);
      if (n.children?.length) walk(n.children);
    }
  }
  walk(nodes);
  return result;
}

function treeToFlow(
  groups: GroupData[],
  activeLayer: string,
  nodeStatuses: Record<string, string>,
): { nodes: Node[]; edges: Edge[] } {
  const flat = flattenTree(groups);
  const nodes: Node[] = flat.map((g) => ({
    id: g.id,
    type: "orgNode",
    position: { x: g.position_x, y: g.position_y },
    data: {
      label: g.name,
      area: g.area,
      role: g.tarea_general,
      email: g.email || "",
      memberCount: g.member_count,
      level: g.nivel_jerarquico,
      nodeType: g.node_type || "area",
      contextNotes: g.context_notes ?? null,
      activeLayer,
      interviewStatus: nodeStatuses[g.id] || "none",
    },
  }));

  const edges: Edge[] = flat
    .filter((g) => g.parent_group_id)
    .map((g) => ({
      id: `e-${g.parent_group_id}-${g.id}`,
      source: g.parent_group_id!,
      target: g.id,
      type: "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#94a3b8", strokeWidth: 2 },
    }));

  return { nodes, edges };
}

export default function CanvasPage() {
  const { user, loading: authLoading } = useAuth();
  const orgId = user?.organization_id ?? "";

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(true);
  const [isEmpty, setIsEmpty] = useState(false);
  const [activeLayer, setActiveLayer] = useState<string>("estructura");
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, string>>({});
  const [collectionRefreshKey, setCollectionRefreshKey] = useState(0);
  const [thresholdMet, setThresholdMet] = useState(false);
  const [diagnosis, setDiagnosis] = useState<DiagnosisResult | null>(null);
  const [structureType, setStructureType] = useState<StructureType>("areas");
  const [showNodeTypeSelector, setShowNodeTypeSelector] = useState(false);
  const [showDocuments, setShowDocuments] = useState(false);
  // Analysis layer state
  const [activeDimension,   setActiveDimension]   = useState<string | null>(null);
  const [showNarrative,     setShowNarrative]     = useState(false);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string> | null>(null);
  const dragTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rawGroupsRef = useRef<GroupData[]>([]);

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

  // Load org structure type
  useEffect(() => {
    if (!orgId) return;
    getOrganization(orgId)
      .then((org) => {
        if (org.org_structure_type) {
          setStructureType(org.org_structure_type as StructureType);
        }
      })
      .catch(() => {});
  }, [orgId]);

  const loadGroups = useCallback(async () => {
    if (!orgId) return;
    try {
      const tree = await getOrgGroups(orgId);
      rawGroupsRef.current = tree || [];
      if (!tree || tree.length === 0) {
        setIsEmpty(true);
        setNodes([]);
        setEdges([]);
      } else {
        setIsEmpty(false);
        const { nodes: n, edges: e } = treeToFlow(tree, activeLayer, nodeStatuses);
        setNodes(n);
        setEdges(e);
      }
    } catch {
      setIsEmpty(true);
    } finally {
      setLoading(false);
    }
  }, [orgId, setNodes, setEdges, activeLayer, nodeStatuses]);

  const loadMeta = useCallback(async () => {
    if (!orgId) return;
    try {
      const [collStatus, diag] = await Promise.allSettled([
        getCollectionStatus(orgId),
        getLatestDiagnosis(orgId),
      ]);
      if (collStatus.status === "fulfilled") {
        setThresholdMet(collStatus.value.threshold_met);
        setNodeStatuses(collStatus.value.node_statuses ?? {});
      }
      if (diag.status === "fulfilled" && diag.value && diag.value.status === "ready") {
        setDiagnosis(diag.value);
      }
    } catch { /* ignore */ }
  }, [orgId]);

  useEffect(() => { loadGroups(); }, [loadGroups]);
  useEffect(() => { loadMeta(); }, [loadMeta]);

  // Re-render nodes when layer or analysis/results state changes
  useEffect(() => {
    if (rawGroupsRef.current.length > 0) {
      const { nodes: n, edges: e } = treeToFlow(rawGroupsRef.current, activeLayer, nodeStatuses);

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
    }
  }, [
    activeLayer, nodeStatuses, diagnosis,
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
    setIsEmpty(false);
    setNodes((nds) => [
      ...nds,
      {
        id: newNode.id,
        type: "orgNode",
        position: { x: newNode.position_x, y: newNode.position_y },
        data: {
          label: newNode.name,
          area: newNode.area || "",
          role: newNode.tarea_general || "",
          email: newNode.email || "",
          memberCount: 0,
          level: newNode.nivel_jerarquico,
          nodeType: newNode.node_type || nodeType,
          contextNotes: null,
          activeLayer,
          interviewStatus: "none",
        },
      },
    ]);
    setSelectedNode(newNode.id);
  }

  async function handleUpdateNode(nodeId: string, data: Record<string, any>) {
    await updateGroup(nodeId, data);
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId
          ? {
              ...n,
              data: {
                ...n.data,
                label: data.name ?? n.data.label,
                area: data.area ?? n.data.area,
                role: data.tarea_general ?? n.data.role,
                email: data.email ?? n.data.email,
                level: data.nivel_jerarquico ?? n.data.level,
              },
            }
          : n
      )
    );
  }

  async function handleDeleteNode(nodeId: string) {
    await deleteGroup(nodeId);
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) =>
      eds.filter((e) => e.source !== nodeId && e.target !== nodeId)
    );
    setSelectedNode(null);
    if (nodes.length <= 1) setIsEmpty(true);
  }

  async function handleTemplateApplied() {
    await loadGroups();
  }

  function handleCollectionChanged() {
    setCollectionRefreshKey((k) => k + 1);
    loadGroups();
    loadMeta();
  }

  if (authLoading || loading) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: "#0D0D14" }}>
        <div className="w-8 h-8 border-2 border-white/10 border-t-white/60 rounded-full animate-spin" />
      </div>
    );
  }

  const selectedNodeData = selectedNode
    ? nodes.find((n) => n.id === selectedNode)
    : null;

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
          onChange={setActiveLayer}
          hasNodes={nodes.length > 0}
          thresholdMet={thresholdMet}
          hasDiagnosis={!!diagnosis}
        />

        {/* Collection progress bar */}
        {activeLayer === "recoleccion" && (
          <CollectionProgress orgId={orgId} refreshKey={collectionRefreshKey} />
        )}

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

          {/* Side panel — changes based on active layer */}
          {selectedNodeData && activeLayer === "estructura" && (
            <SidePanel
              nodeId={selectedNode!}
              orgId={orgId}
              data={selectedNodeData.data}
              onUpdate={handleUpdateNode}
              onDelete={handleDeleteNode}
              onClose={() => setSelectedNode(null)}
            />
          )}

          {selectedNodeData && activeLayer === "recoleccion" && (
            <CollectionPanel
              orgId={orgId}
              nodeId={selectedNode!}
              nodeName={selectedNodeData.data.label}
              nodeEmail={selectedNodeData.data.email || ""}
              interviewStatus={selectedNodeData.data.interviewStatus || "none"}
              onClose={() => setSelectedNode(null)}
              onChanged={handleCollectionChanged}
              onSwitchToEstructura={() => setActiveLayer("estructura")}
            />
          )}

          {/* Analysis layer — no diagnosis yet: show verify-data prompt */}
          {activeLayer === "analisis" && !diagnosis && (
            <AnalysisLayer
              orgId={orgId}
              onDiagnosisGenerated={() => {
                loadMeta();
                setActiveLayer("resultados");
              }}
            />
          )}

          {/* Analysis layer — diagnosis processing */}
          {activeLayer === "analisis" && diagnosis?.status === "processing" && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-50/80 backdrop-blur-sm z-5">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-gray-500 mx-auto mb-3" />
                <p className="text-sm font-medium text-gray-700">Diagnóstico en proceso…</p>
                <p className="text-xs text-gray-400 mt-1">
                  El procesador externo está analizando los datos. Esto puede tomar unos minutos.
                </p>
              </div>
            </div>
          )}

          {/* Analysis layer — ready: node panel on click */}
          {selectedNodeData && activeLayer === "analisis" && diagnosis?.status === "ready" && (
            <AnalysisNodePanel
              nodeId={selectedNode!}
              nodeName={selectedNodeData.data.label}
              diagnosis={diagnosis}
              onClose={() => setSelectedNode(null)}
              onViewNarrative={() => setShowNarrative(true)}
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
              }}
              onHighlightNodes={
                showNarrative ? handleHighlightNodes : handleHighlightNodesInMap
              }
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
