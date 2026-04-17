const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || res.statusText);
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
  localStorage.setItem("access_token", data.access_token);
  return data;
}

export async function register(email: string, password: string, name: string) {
  return request<{ id: string; email: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export async function getMe() {
  return request<import("./types").User>("/auth/me");
}

export async function logout() {
  await request("/auth/logout", { method: "POST" });
  localStorage.removeItem("access_token");
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

// ── Free Member Interview (public, no auth) ─────────
export async function getFreeInterview(token: string) {
  return request<{
    name: string;
    role: string;
    token: string;
    assessment_id: string;
    submitted: boolean;
    responses: Record<string, number> | null;
  }>(`/api/quick-assessment/interview/${token}`);
}

export async function submitFreeInterview(
  token: string,
  responses: Record<string, number>
) {
  return request<{ status: string }>(
    `/api/quick-assessment/interview/${token}/submit`,
    {
      method: "POST",
      body: JSON.stringify({ token, responses }),
    }
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

// ── Organizations ────────────────────────────────────
export async function getOrganization(orgId: string) {
  return request<import("./types").Organization>(`/organizations/${orgId}`);
}

export async function getOrgStats(orgId: string) {
  return request<Record<string, number>>(`/organizations/${orgId}/stats`);
}
