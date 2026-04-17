export interface QuickAssessment {
  id: string;
  organization_id: string;
  leader_responses: Record<string, number | string>;
  scores: Record<string, number>;
  member_count: number;
  status: "waiting" | "ready" | "completed";
  created_at: string;
}

export interface QuickAssessmentMember {
  id: string;
  assessment_id: string;
  name: string;
  role_label: string;
  email: string;
  token: string;
  completed: boolean;
  created_at: string;
}

export interface Progress {
  total_invited: number;
  total_completed: number;
  threshold: number;
  ready: boolean;
}

export interface ScoreResponse {
  assessment_id: string;
  scores: Record<string, number>;
  member_count: number;
  status: "waiting" | "ready" | "completed";
}

export interface Question {
  id: string;
  dimension: string;
  texto: string;
  tipo: "likert" | "abierta";
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
}
