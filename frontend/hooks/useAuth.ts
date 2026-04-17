"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

/**
 * Auth guard hook. Redirects to /login if no valid token.
 * Returns the current user once authenticated.
 */
export function useAuth() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    getMe()
      .then((u) => {
        setUser(u);
        setLoading(false);
      })
      .catch((err) => {
        // Token invalid/expired and refresh failed — redirect
        if (err instanceof ApiError && err.status === 401) {
          localStorage.removeItem("access_token");
          router.replace("/login");
        }
        setLoading(false);
      });
  }, [router]);

  return { user, loading };
}
