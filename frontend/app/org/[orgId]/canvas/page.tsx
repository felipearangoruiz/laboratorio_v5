"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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
} from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import OrgNode from "./OrgNode";
import SidePanel from "./SidePanel";
import CollectionPanel from "./CollectionPanel";
import CollectionProgress from "./CollectionProgress";
import AnalysisLayer from "./AnalysisLayer";
import DiagnosisPanel from "./DiagnosisPanel";
import Sidebar from "./Sidebar";
import EmptyState from "./EmptyState";
import LayerSelector from "./LayerSelector";
import { Plus, User, Users } from "lucide-react";

const nodeTypes = { orgNode: OrgNode };

type StructureType = "people" | "areas" | "mixed";

interface GroupData {
  id: string;
  name: string;
  description: string;
  node_type: string;
  email: string;
  area: string;
  tarea_general: string;
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
  const [diagnosis, setDiagnosis] = useState<any>(null);
  const [structureType, setStructureType] = useState<StructureType>("areas");
  const [showNodeTypeSelector, setShowNodeTypeSelector] = useState(false);
  const dragTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rawGroupsRef = useRef<GroupData[]>([]);

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
      }
      if (diag.status === "fulfilled" && diag.value && diag.value.status === "completed") {
        setDiagnosis(diag.value);
      }
    } catch { /* ignore */ }
  }, [orgId]);

  useEffect(() => { loadGroups(); }, [loadGroups]);
  useEffect(() => { loadMeta(); }, [loadMeta]);

  // Re-render nodes when layer changes
  useEffect(() => {
    if (rawGroupsRef.current.length > 0) {
      const { nodes: n, edges: e } = treeToFlow(rawGroupsRef.current, activeLayer, nodeStatuses);
      setNodes(n);
      setEdges(e);
    }
  }, [activeLayer, nodeStatuses, setNodes, setEdges]);

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
  }

  if (authLoading || loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    );
  }

  const selectedNodeData = selectedNode
    ? nodes.find((n) => n.id === selectedNode)
    : null;

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50">
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        orgId={orgId}
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
              <Background color="#e2e8f0" gap={20} />
              <Controls showInteractive={false} />

              {activeLayer === "estructura" && (
                <Panel position="bottom-right">
                  <div className="relative">
                    {/* Node type selector for mixed mode */}
                    {showNodeTypeSelector && (
                      <div className="absolute bottom-14 right-0 bg-white rounded-xl shadow-lg border border-gray-200 py-2 w-48">
                        <button
                          onClick={() => createNodeOfType("person")}
                          className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 text-left"
                        >
                          <User className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-700">Persona</span>
                        </button>
                        <button
                          onClick={() => createNodeOfType("area")}
                          className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 text-left"
                        >
                          <Users className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-700">Área</span>
                        </button>
                      </div>
                    )}
                    <button
                      onClick={() => handleAddNode()}
                      className="w-12 h-12 bg-gray-900 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-gray-800 transition-colors"
                      title="Agregar nodo"
                    >
                      <Plus className="w-5 h-5" />
                    </button>
                  </div>
                </Panel>
              )}
            </ReactFlow>
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
              onClose={() => setSelectedNode(null)}
              onChanged={handleCollectionChanged}
            />
          )}

          {/* Analysis layer overlay */}
          {activeLayer === "analisis" && !diagnosis && (
            <AnalysisLayer
              orgId={orgId}
              onDiagnosisGenerated={() => {
                loadMeta();
                setActiveLayer("resultados");
              }}
            />
          )}

          {/* Results panel */}
          {activeLayer === "resultados" && diagnosis && (
            <DiagnosisPanel
              diagnosis={diagnosis}
              onClose={() => setActiveLayer("estructura")}
            />
          )}
        </div>
      </div>
    </div>
  );
}
