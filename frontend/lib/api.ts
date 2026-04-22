import type {
  Node as ApiNode,
  NodeCreate,
  NodeUpdate,
  Edge as ApiEdge,
  EdgeCreate,
  EdgeUpdate,
  AssessmentCampaign,
  CampaignCreate,
  CampaignUpdate,
  NodeState,
  NodeStateCreate,
  NodeStateUpdate,
  NodeStateStatus,
} from "./types";
import {
  getAuthToken,
  authHeader,
  setAuthToken,
  clearAuth,
} from "./auth-utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function tryRefreshToken(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return false;
    const data = await res.json();
    setAuthToken(data.access_token);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  _retried = false,
): Promise<T> {
  const token = getAuthToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeader(),
    ...(options.headers as Record<string, string>),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  // Auto-refresh on 401 (token expired), retry once. Only redirect to /login
  // if the caller was actually trying to authenticate (had a token). For
  // anonymous requests to public endpoints, propagate the error to the caller
  // instead of hijacking the user out of the flow (e.g., free onboarding).
  if (res.status === 401 && !_retried) {
    if (token) {
      const refreshed = await tryRefreshToken();
      if (refreshed) {
        return request<T>(path, options, true);
      }
      // Refresh failed and we had a token — user's session is invalid,
      // send them to login.
      if (typeof window !== "undefined") {
        clearAuth();
        window.location.href = "/login";
      }
    }
    // No token was sent → 401 from a public endpoint is unexpected but must
    // NOT redirect. Fall through to raise ApiError below.
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  // 204 No Content — successful but no body to parse (DELETE endpoints)
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Auth ──────────────────────────────────────────────
export async function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
    credentials: "include",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || "Error al iniciar sesión");
  }

  const data = await res.json();
  setAuthToken(data.access_token);
  return data;
}

export async function register(
  email: string,
  password: string,
  name: string,
  orgName: string = "",
) {
  return request<{ id: string; email: string; organization_id: string }>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify({ email, password, name, org_name: orgName }),
    }
  );
}

export async function getMe() {
  return request<import("./types").User>("/auth/me");
}

/**
 * Safe version of getMe that returns null instead of redirecting on 401.
 * Use on public pages that optionally show auth-dependent UI.
 */
export async function getMeSafe(): Promise<import("./types").User | null> {
  const token = getAuthToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { ...authHeader() },
      credentials: "include",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function logout() {
  await request("/auth/logout", { method: "POST" });
  clearAuth();
}

// ── Quick Assessment (Free MVP) ──────────────────────
export async function createQuickAssessment(
  data: import("./types").QuickAssessmentCreate
) {
  return request<{ id: string }>("/api/quick-assessment", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function inviteMembers(
  assessmentId: string,
  members: import("./types").QuickAssessmentMemberInvite[]
) {
  return request<{ invited: number }>(`/api/quick-assessment/${assessmentId}/invite`, {
    method: "POST",
    body: JSON.stringify({ members }),
  });
}

export async function submitMemberResponse(
  assessmentId: string,
  token: string,
  responses: Record<string, number>
) {
  return request<{ status: string }>(`/api/quick-assessment/${assessmentId}/respond`, {
    method: "POST",
    body: JSON.stringify({ token, responses }),
  });
}

export async function getAssessmentScore(assessmentId: string) {
  return request<import("./types").QuickAssessmentScore>(
    `/api/quick-assessment/${assessmentId}/score`
  );
}

export async function getAssessmentMembers(assessmentId: string) {
  return request<
    {
      id: string;
      name: string;
      role: string;
      email: string;
      token: string;
      submitted: boolean;
    }[]
  >(`/api/quick-assessment/${assessmentId}/members`);
}

// ── Free flow: preguntas del instrumento v2 ──────────
export async function getLeaderQuestions() {
  return request<{
    questions: import("./types").V2Question[];
    dimensions: Record<string, string>;
  }>("/api/quick-assessment/leader-questions");
}

// ── Free Member Interview (public, no auth) ─────────
// Devuelve el estado del miembro + las preguntas a responder (10 base + 3
// adaptativas seleccionadas según hipótesis del gerente).
export async function getFreeInterview(token: string) {
  return request<{
    name: string;
    role: string;
    token: string;
    assessment_id: string;
    submitted: boolean;
    responses: Record<string, any> | null;
    questions: import("./types").V2Question[];
    dimensions: Record<string, string>;
  }>(`/api/quick-assessment/interview/${token}`);
}

export async function submitFreeInterview(
  token: string,
  responses: Record<string, any>,
) {
  return request<{ status: string }>(
    `/api/quick-assessment/interview/${token}/submit`,
    {
      method: "POST",
      body: JSON.stringify({ token, responses }),
    },
  );
}

// ── Public Interview (existing premium endpoints) ────
export async function getPublicInterview(token: string) {
  return request<import("./types").PublicInterview>(`/entrevista/${token}`);
}

export async function submitInterview(token: string, data: Record<string, any>) {
  return request<import("./types").PublicInterview>(`/entrevista/${token}/submit`, {
    method: "POST",
    body: JSON.stringify({ data }),
  });
}

export async function saveDraft(token: string, data: Record<string, any>) {
  return request<import("./types").PublicInterview>(`/entrevista/${token}/draft`, {
    method: "POST",
    body: JSON.stringify({ data }),
  });
}

// ── Canvas / Groups (legacy) ─────────────────────────
// Los 4 helpers siguientes consumen los routers `/groups` del
// compat layer (Sprint 1.4). Serán reemplazados en Sprint 2.3
// por `listNodes` / `createNode` / `updateNode` / `deleteNode`.
// `any` se conserva en estos 3 helpers para no romper al
// consumer `canvas/page.tsx` (que los tipa como GroupData
// inline). Tiparlos como `unknown` fuerza refactor del
// consumer, que es trabajo del Sprint 2.3.
/** @deprecated — usar listNodes después del Sprint 2.3 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function getOrgGroups(orgId: string) {
  return request<any[]>(`/organizations/${orgId}/groups/tree`);
}

/** @deprecated — usar createNode después del Sprint 2.3 */
export async function createGroup(data: {
  organization_id: string;
  node_type?: string;
  name: string;
  description?: string;
  tarea_general?: string;
  email?: string;
  area?: string;
  nivel_jerarquico?: number;
  parent_group_id?: string | null;
  position_x?: number;
  position_y?: number;
}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return request<any>("/groups", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/** @deprecated — usar updateNode después del Sprint 2.3 */
export async function updateGroup(
  groupId: string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: Record<string, any>,
) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return request<any>(`/groups/${groupId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/** @deprecated — usar deleteNode después del Sprint 2.3 */
export async function deleteGroup(groupId: string) {
  return request<void>(`/groups/${groupId}`, { method: "DELETE" });
}

export async function updatePositions(
  orgId: string,
  positions: { id: string; position_x: number; position_y: number }[]
) {
  return request<{ updated: number }>(
    `/organizations/${orgId}/groups/positions`,
    {
      method: "PATCH",
      body: JSON.stringify({ positions }),
    }
  );
}

export async function getTemplates(orgId: string) {
  return request<{ id: string; name: string; description: string }[]>(
    `/organizations/${orgId}/canvas/templates`
  );
}

export async function applyTemplate(orgId: string, templateId: string) {
  return request<{ created: number; nodes: unknown[] }>(
    `/organizations/${orgId}/canvas/templates/${templateId}`,
    { method: "POST" }
  );
}

export async function importCsv(
  orgId: string,
  rows: { name: string; role: string; area: string; boss: string }[]
) {
  return request<{ created: number }>(
    `/organizations/${orgId}/canvas/import-csv`,
    {
      method: "POST",
      body: JSON.stringify({ rows }),
    }
  );
}

// ── Collection (Fase 2) ─────────────────────────────
export async function inviteFromNode(
  orgId: string,
  nodeId: string,
  data: { name: string; role_label?: string }
) {
  return request<{
    member_id: string;
    token: string;
    interview_link: string;
    status: string;
    email: string;
  }>(
    `/organizations/${orgId}/nodes/${nodeId}/invite`,
    { method: "POST", body: JSON.stringify(data) }
  );
}

export async function sendReminder(memberId: string) {
  return request<{ status: string; reminder_count: number }>(
    `/members/${memberId}/remind`,
    { method: "POST" }
  );
}

export async function revokeInvitation(memberId: string) {
  return request<{ status: string }>(
    `/members/${memberId}/revoke`,
    { method: "POST" }
  );
}

export async function getCollectionStatus(orgId: string) {
  return request<{
    total_nodes: number;
    total_members: number;
    by_status: Record<string, number>;
    completed: number;
    nodes_with_interview: number;
    threshold_percent: number;
    threshold_met: boolean;
    node_statuses: Record<string, string>;
  }>(`/organizations/${orgId}/collection/status`);
}

export async function getNodeInterviews(orgId: string, nodeId: string) {
  return request<{
    member_id: string;
    name: string;
    role_label: string;
    interview_token: string;
    token_status: string;
    submitted_at: string | null;
    reminder_count: number;
  }[]>(`/organizations/${orgId}/nodes/${nodeId}/interviews`);
}

/**
 * @deprecated — el shape del instrumento premium no está
 * tipado todavía. Pendiente tipar contra el response real
 * (ver deuda Sprint 2.3).
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function getPremiumQuestions() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return request<any>("/interview/premium/questions");
}

// ── Documents (institutional files) ─────────────────
export async function getDocuments(orgId: string) {
  return request<{
    id: string;
    organization_id: string;
    label: string;
    doc_type: string;
    filename: string;
    created_at: string;
  }[]>(`/organizations/${orgId}/documents`);
}

export async function uploadDocument(
  orgId: string,
  file: File,
  label: string,
  docType: string = "institutional"
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("label", label);
  formData.append("doc_type", docType);

  const res = await fetch(`${API_BASE}/organizations/${orgId}/documents`, {
    method: "POST",
    headers: { ...authHeader() },
    body: formData,
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  return res.json();
}

export async function deleteDocument(orgId: string, docId: string) {
  return request<void>(`/organizations/${orgId}/documents/${docId}`, { method: "DELETE" });
}

// ── Diagnosis ────────────────────────────────────────
// Status lifecycle: 'processing' → 'ready' | 'failed'

// ── Shared finding / recommendation types ────────────────────────
// Supports both the legacy Codex format and the new motor de análisis.
//
// Legacy Codex:  confidence="high"|"medium"|"low", dimension=string
// Motor nuevo:   confidence=float (0–1), dimensions=string[], type="observacion"|"patron"|...

export interface DiagnosisFinding {
  id: string;
  title: string;
  description: string;
  type: string; // "observacion"|"patron"|"inferencia"|"hipotesis" OR legacy "strength"|"fortaleza"
  /** Legacy: "high"|"medium"|"low". New motor: float 0–1. */
  confidence: string | number;
  node_ids: string[];
  /** Legacy single dimension */
  dimension?: string;
  /** New motor: list of dimensions */
  dimensions?: string[];
  /** New motor fields */
  severity?: string;
  confidence_rationale?: string;
}

export interface DiagnosisRecommendation {
  id: string;
  priority: number;
  title: string;
  description: string;
  node_ids: string[];
  /** New motor fields */
  impact?: string;
  effort?: string;
  horizon?: string;
}

export interface DiagnosisResult {
  id: string;
  organization_id: string;
  status: "processing" | "ready" | "failed";
  scores: Record<string, { score: number; avg: number; std: number; node_scores: Record<string, number> }>;
  findings: DiagnosisFinding[];
  recommendations: DiagnosisRecommendation[];
  narrative_md: string;
  structure_snapshot: Record<string, unknown>;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export async function getLatestDiagnosis(orgId: string) {
  return request<DiagnosisResult | null>(`/organizations/${orgId}/diagnosis/latest`);
}

export async function createDiagnosis(orgId: string, data: Omit<DiagnosisResult, "id" | "organization_id" | "status" | "error" | "created_at" | "completed_at">) {
  return request<DiagnosisResult>(`/organizations/${orgId}/diagnosis`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getNodeDiagnosis(orgId: string, diagnosisId: string, nodeId: string) {
  return request<{
    node_id: string;
    scores: Record<string, { score: number; avg: number; std: number }>;
    findings: DiagnosisResult["findings"];
    recommendations: DiagnosisResult["recommendations"];
  }>(`/organizations/${orgId}/diagnosis/${diagnosisId}/node/${nodeId}`);
}

export async function getDiagnosisInput(orgId: string) {
  return request<Record<string, unknown>>(`/organizations/${orgId}/diagnosis/input`);
}

// ── Analysis Motor (pipeline 4 pasos) ────────────────────────────

/** Resultado completo del análisis de un nodo individual (Paso 1). */
export interface NodeAnalysisRead {
  id: string;
  run_id: string;
  org_id: string;
  group_id: string;
  signals_positive: string[];
  signals_tension: string[];
  themes: string[];
  dimensions_touched: string[];
  evidence_type: string | null;    // "observacion"|"juicio"|"hipotesis"
  emotional_intensity: string | null; // "baja"|"media"|"alta"
  key_quotes: string[];
  context_notes_used: boolean;
  confidence: number;              // 0.0 – 1.0
  created_at: string;
}

/** Estado del analysis_run más reciente de la organización. */
export interface AnalysisRunStatus {
  status: "none" | "pending" | "running" | "completed" | "failed";
  run_id?: string;
  started_at?: string;
  completed_at?: string;
  total_nodes: number;
  total_groups: number;
  error_message?: string | null;
}

/** Estado del último analysis_run de la organización.
 *  Devuelve { status: "none" } si no hay ninguna corrida. */
export async function getAnalysisStatus(orgId: string) {
  return request<AnalysisRunStatus>(`/organizations/${orgId}/analysis/status`);
}

/** node_analysis más reciente para un nodo (null si no existe). */
export async function getNodeAnalysis(orgId: string, groupId: string) {
  return request<NodeAnalysisRead | null>(
    `/organizations/${orgId}/analysis/latest/nodes/${groupId}`
  );
}

/** Abre una nueva corrida de análisis (para botón "Generar diagnóstico"). */
export async function triggerAnalysisRun(
  orgId: string,
  opts?: { model_used?: string; total_nodes?: number; total_groups?: number }
) {
  return request<{ run_id: string; status: string }>(
    `/organizations/${orgId}/analysis/runs`,
    {
      method: "POST",
      body: JSON.stringify(opts ?? {}),
    }
  );
}

// ── Organizations ────────────────────────────────────
export async function getOrganization(orgId: string) {
  return request<import("./types").Organization>(`/organizations/${orgId}`);
}

export async function updateOrganization(orgId: string, data: Record<string, any>) {
  return request<import("./types").Organization>(`/organizations/${orgId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getOrgStats(orgId: string) {
  return request<Record<string, number>>(`/organizations/${orgId}/stats`);
}

// ============================================================
// Sprint 1.6 — API client del nuevo modelo (Node/Edge/Campaign)
// ============================================================
// Funciones aditivas que consumen los routers `/nodes`,
// `/edges`, `/campaigns` y `/node-states`. Coexisten con los
// helpers legacy (getOrgGroups, createGroup, etc.) durante la
// fase de coexistencia del refactor. Ningún componente
// existente las consume aún — Sprint 2 arranca la migración.
//
// Patrón de URL verificado en backend/app/routers/*.py:
//   GET  /nodes?organization_id=…&type=…&parent_node_id=…
//   GET  /nodes/{id}
//   POST /nodes
//   PATCH /nodes/{id}
//   DELETE /nodes/{id}  (204, soft-delete)
// Mismo patrón para /edges, /campaigns, /node-states.
// Filtro de status en /node-states usa query param `status`
// (alias del parámetro `status_filter` en FastAPI).

function buildQuery(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== "",
  ) as [string, string][];
  if (entries.length === 0) return "";
  const qs = new URLSearchParams(entries).toString();
  return `?${qs}`;
}

// ── /nodes ───────────────────────────────────────────
export async function listNodes(organizationId?: string) {
  const qs = buildQuery({ organization_id: organizationId });
  return request<ApiNode[]>(`/nodes${qs}`);
}

export async function getNode(id: string) {
  return request<ApiNode>(`/nodes/${id}`);
}

export async function createNode(payload: NodeCreate) {
  return request<ApiNode>("/nodes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateNode(id: string, payload: NodeUpdate) {
  return request<ApiNode>(`/nodes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteNode(id: string) {
  return request<void>(`/nodes/${id}`, { method: "DELETE" });
}

// ── /edges ───────────────────────────────────────────
export async function listEdges(organizationId?: string) {
  const qs = buildQuery({ organization_id: organizationId });
  return request<ApiEdge[]>(`/edges${qs}`);
}

export async function getEdge(id: string) {
  return request<ApiEdge>(`/edges/${id}`);
}

export async function createEdge(payload: EdgeCreate) {
  return request<ApiEdge>("/edges", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateEdge(id: string, payload: EdgeUpdate) {
  return request<ApiEdge>(`/edges/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteEdge(id: string) {
  return request<void>(`/edges/${id}`, { method: "DELETE" });
}

// ── /campaigns ───────────────────────────────────────
export async function listCampaigns(organizationId?: string) {
  const qs = buildQuery({ organization_id: organizationId });
  return request<AssessmentCampaign[]>(`/campaigns${qs}`);
}

export async function getCampaign(id: string) {
  return request<AssessmentCampaign>(`/campaigns/${id}`);
}

export async function createCampaign(payload: CampaignCreate) {
  return request<AssessmentCampaign>("/campaigns", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCampaign(id: string, payload: CampaignUpdate) {
  return request<AssessmentCampaign>(`/campaigns/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

// ── /node-states ─────────────────────────────────────
export async function listNodeStates(filters?: {
  node_id?: string;
  campaign_id?: string;
  status?: NodeStateStatus;
}) {
  const qs = buildQuery({
    node_id: filters?.node_id,
    campaign_id: filters?.campaign_id,
    status: filters?.status,
  });
  return request<NodeState[]>(`/node-states${qs}`);
}

export async function getNodeState(id: string) {
  return request<NodeState>(`/node-states/${id}`);
}

export async function createNodeState(payload: NodeStateCreate) {
  return request<NodeState>("/node-states", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateNodeState(id: string, payload: NodeStateUpdate) {
  return request<NodeState>(`/node-states/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
