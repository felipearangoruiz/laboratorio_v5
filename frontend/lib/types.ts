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
  leader_responses: Record<string, number>;
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

export interface FreeDimension {
  id: string;
  label: string;
  questions: FreeQuestion[];
}

export interface FreeQuestion {
  id: string;
  text: string;
  type: "likert";
  dimension: string;
}

export const FREE_DIMENSIONS: FreeDimension[] = [
  {
    id: "liderazgo",
    label: "Liderazgo",
    questions: [
      {
        id: "free_lid_01",
        text: "Las decisiones importantes se toman de forma oportuna en esta organización.",
        type: "likert",
        dimension: "liderazgo",
      },
      {
        id: "free_lid_02",
        text: "Los líderes son accesibles cuando se necesita su orientación.",
        type: "likert",
        dimension: "liderazgo",
      },
    ],
  },
  {
    id: "comunicacion",
    label: "Comunicación",
    questions: [
      {
        id: "free_com_01",
        text: "La información fluye de manera clara entre las áreas de la organización.",
        type: "likert",
        dimension: "comunicacion",
      },
      {
        id: "free_com_02",
        text: "Las personas saben a quién acudir cuando tienen dudas sobre su trabajo.",
        type: "likert",
        dimension: "comunicacion",
      },
    ],
  },
  {
    id: "cultura",
    label: "Cultura",
    questions: [
      {
        id: "free_cul_01",
        text: "Existe confianza entre los miembros del equipo.",
        type: "likert",
        dimension: "cultura",
      },
      {
        id: "free_cul_02",
        text: "Los valores de la organización se reflejan en las decisiones del día a día.",
        type: "likert",
        dimension: "cultura",
      },
    ],
  },
  {
    id: "operacion",
    label: "Operación",
    questions: [
      {
        id: "free_op_01",
        text: "Los procesos internos permiten trabajar de forma eficiente.",
        type: "likert",
        dimension: "operacion",
      },
      {
        id: "free_op_02",
        text: "Cuando algo falla, existe un mecanismo claro para resolverlo.",
        type: "likert",
        dimension: "operacion",
      },
    ],
  },
];
