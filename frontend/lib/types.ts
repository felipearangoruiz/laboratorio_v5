export interface JWTPayload {
  user_id: string;
  role: "superadmin" | "admin";
  organization_id: string | null;
  exp: number;
}

export interface ApiUser {
  id: string;
  email: string;
  role: string;
  organization_id: string | null;
}
