"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const apiBaseUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
      const response = await fetch(`${apiBaseUrl}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
      });

      if (!response.ok) {
        throw new Error("Credenciales inválidas");
      }

      const data = (await response.json()) as { access_token: string };
      document.cookie = `auth_token=${data.access_token}; path=/; max-age=900`;
      router.push("/admin");
    } catch (err) {
      if (err instanceof Error) {
        if (err.message === "Failed to fetch") {
          setError("No se pudo conectar con el servidor. Intenta nuevamente.");
        } else {
          setError(err.message);
        }
      } else {
        setError("Error al iniciar sesión");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ maxWidth: 360, margin: "4rem auto" }}>
      <h1>Iniciar sesión</h1>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            style={{ display: "block", width: "100%" }}
          />
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            style={{ display: "block", width: "100%" }}
          />
        </div>

        {error ? (
          <p role="alert" style={{ color: "crimson", marginBottom: "1rem" }}>
            {error}
          </p>
        ) : null}

        <button type="submit" disabled={loading}>
          {loading ? "Ingresando..." : "Ingresar"}
        </button>
      </form>
    </main>
  );
}
