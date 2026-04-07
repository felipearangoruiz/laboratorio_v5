"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../lib/apiFetch";
import type { ApiUser } from "../lib/types";

export function useSession() {
  const [user, setUser] = useState<ApiUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const sessionUser = await apiFetch<ApiUser>("/auth/me");
        setUser(sessionUser);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar la sesión");
      } finally {
        setLoading(false);
      }
    };

    void fetchSession();
  }, []);

  return { user, loading, error };
}
