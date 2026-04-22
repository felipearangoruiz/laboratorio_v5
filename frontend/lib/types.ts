export interface User {
  id: string;
  email: string;
  role: "SUPERADMIN" | "ADMIN";
  organization_id: string | null;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  description: string;
  sector: string;
  strategic_objectives: string;
  strategic_concerns: string;
  key_questions: string;
  additional_context: string;
  org_structure_type: "people" | "areas" | "mixed";
  admin_id: string | null;
  created_at: string;
}

export interface Member {
  id: string;
  organization_id: string;
  group_id: string | null;
  name: string;
  role_label: string;
  interview_token: string;
  token_status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "EXPIRED";
  created_at: string;
}

export interface QuickAssessmentCreate {
  org_name: string;
  org_type: string;
  size_range: string;
  leader_responses: Record<string, any>;
}

export interface QuickAssessmentMemberInvite {
  name: string;
  role: string;
  email: string;
}

export interface QuickAssessmentScore {
  id: string;
  org_name: string;
  dimensions: DimensionScore[];
  member_count: number;
  responses_count: number;
  created_at: string;
}

export interface DimensionScore {
  dimension: string;
  label: string;
  score: number;
  max_score: number;
}

export interface PublicInterview {
  member_id: string;
  name: string;
  role_label: string;
  token_status: string;
  submitted_at: string | null;
  data: Record<string, any> | null;
  schema_version: number;
}

// ── Instrument v2 types ─────────────────────────────────

export interface V2Layer {
  id: string;
  type: string;
  condition: Record<string, any>;
  text: string;
  options?: string[];
  frequency_options?: string[];
  severity_options?: string[];
  max_items?: number;
}

export interface V2Question {
  id: string;
  title: string;
  dimension: string;
  paired_with?: string;
  hypothesis?: string;
  activation_rule?: Record<string, any>;
  base: {
    text: string;
    type: string;
    options: string[];
  };
  layers: V2Layer[];
  output_template?: string;
}

export interface V2Section {
  dimension: string;
  label: string;
  questions: V2Question[];
}

// Free flow subset — G1-G4 base questions (for onboarding leader survey)
export const FREE_LEADER_QUESTIONS: V2Question[] = [
  {
    id: "G1",
    title: "Distribución de tu tiempo",
    dimension: "centralizacion",
    base: {
      text: "¿Cuánto de tu tiempo en la semana se te va en resolver cosas del día a día que en teoría alguien más podría resolver?",
      type: "single_select",
      options: ["Casi nada", "Menos de la mitad", "Más o menos la mitad", "La mayor parte", "Prácticamente todo"],
    },
    layers: [],
  },
  {
    id: "G2",
    title: "Prueba de ausencia",
    dimension: "centralizacion",
    base: {
      text: "Si te fueras de vacaciones una semana sin poder contestar el teléfono, ¿qué pasaría con la operación?",
      type: "single_select",
      options: ["Todo seguiría funcionando normal", "Algunas cosas se retrasarían", "Varias decisiones quedarían en pausa", "Se frenaría significativamente", "No me puedo ir una semana"],
    },
    layers: [],
  },
  {
    id: "G3",
    title: "Autonomía del equipo",
    dimension: "centralizacion",
    base: {
      text: "¿Cuáles de estas decisiones puede tomar tu equipo SIN consultarte?",
      type: "multi_select",
      options: ["Ofrecer descuentos", "Resolver quejas de clientes", "Compras menores", "Cambiar un proceso", "Contratar ayuda temporal", "Negociar con proveedor", "Ninguna"],
    },
    layers: [],
  },
  {
    id: "G4",
    title: "Cuellos de botella",
    dimension: "cuellos_botella",
    base: {
      text: "¿Dónde se traban las cosas más seguido en tu negocio?",
      type: "multi_select",
      options: ["Aprobaciones que dependen de mí", "Coordinación entre áreas o sedes", "Falta de información", "Falta de herramientas", "Errores y retrabajo", "Proveedores", "Falta de personal", "No se traban"],
    },
    layers: [],
  },
];

export const FREE_DIMENSIONS_V2 = {
  centralizacion: "Centralización",
  cuellos_botella: "Cuellos de botella",
};

// ============================================================
// Sprint 1.6 — Tipos del nuevo modelo (Node + Edge + Campaign)
// ============================================================
// Estos tipos coexisten con los tipos legacy (Group, Member,
// Interview) durante la fase de coexistencia del refactor.
// Los tipos legacy NO se eliminan en este sprint.
//
// Para semántica de cada tipo, ver docs/MODEL_PHILOSOPHY.md.
// Para deuda de migración del frontend, ver
// docs/DEUDA_DOCUMENTAL.md.
//
// Ajustes respecto al spec inicial tras verificar backend
// (backend/app/models/*.py y backend/app/routers/*.py):
//
// - Node NO tiene updated_at (solo created_at + deleted_at).
// - EdgeUpdate del backend acepta edge_type además de
//   edge_metadata (la mutación de edge_type re-valida unicidad).
// - CampaignCreate del backend NO acepta closed_at (solo el
//   PATCH puede setearlo; al transicionar a 'closed' el router
//   lo auto-estampa si no viene).
// - NodeStateRead incluye created_at.
// - NodeStateCreate/Update del backend NO exponen invited_at
//   ni completed_at como campos editables — los gestiona el
//   backend. Se modelan como read-only en el tipo Read.

export type NodeType = "unit" | "person";
export type EdgeType = "lateral" | "process";
export type CampaignStatus = "draft" | "active" | "closed";
export type NodeStateStatus =
  | "invited" | "in_progress" | "completed" | "skipped";

export interface Node {
  id: string;
  organization_id: string;
  parent_node_id: string | null;
  type: NodeType;
  name: string;
  position_x: number;
  position_y: number;
  attrs: Record<string, unknown>;
  created_at: string;
  deleted_at: string | null;
}

export interface NodeCreate {
  organization_id: string;
  type: NodeType;
  name: string;
  parent_node_id?: string | null;
  position_x?: number;
  position_y?: number;
  attrs?: Record<string, unknown>;
}

export interface NodeUpdate {
  name?: string;
  parent_node_id?: string | null;
  position_x?: number;
  position_y?: number;
  attrs?: Record<string, unknown>;
}

export interface Edge {
  id: string;
  organization_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: EdgeType;
  edge_metadata: Record<string, unknown>;
  created_at: string;
  deleted_at: string | null;
}

export interface EdgeCreate {
  organization_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: EdgeType;
  edge_metadata?: Record<string, unknown>;
}

export interface EdgeUpdate {
  edge_type?: EdgeType;
  edge_metadata?: Record<string, unknown>;
}

export interface AssessmentCampaign {
  id: string;
  organization_id: string;
  created_by_user_id: string | null;
  name: string;
  status: CampaignStatus;
  started_at: string | null;
  closed_at: string | null;
  created_at: string;
}

export interface CampaignCreate {
  organization_id: string;
  name: string;
  status?: CampaignStatus;
  started_at?: string | null;
}

export interface CampaignUpdate {
  name?: string;
  status?: CampaignStatus;
  started_at?: string | null;
  closed_at?: string | null;
}

export interface NodeState {
  id: string;
  node_id: string;
  campaign_id: string;
  email_assigned: string | null;
  role_label: string | null;
  context_notes: string | null;
  respondent_token: string | null;
  status: NodeStateStatus;
  interview_data: Record<string, unknown> | null;
  invited_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface NodeStateCreate {
  node_id: string;
  campaign_id: string;
  email_assigned?: string | null;
  role_label?: string | null;
  context_notes?: string | null;
  respondent_token?: string | null;
  status?: NodeStateStatus;
  interview_data?: Record<string, unknown> | null;
}

export interface NodeStateUpdate {
  email_assigned?: string | null;
  role_label?: string | null;
  context_notes?: string | null;
  respondent_token?: string | null;
  status?: NodeStateStatus;
  interview_data?: Record<string, unknown> | null;
}
