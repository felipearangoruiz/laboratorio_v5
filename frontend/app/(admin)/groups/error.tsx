"use client";

import { useEffect } from "react";

type GroupsErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function GroupsError({ error, reset }: GroupsErrorProps) {
  useEffect(() => {
    console.error("Error en /admin/groups:", error);
  }, [error]);

  return (
    <section className="p-6">
      <h2 className="text-lg font-semibold text-red-700">Ocurrió un error al cargar grupos.</h2>
      <p className="mt-2 text-sm text-gray-600">Intenta refrescar o volver a cargar la página.</p>
      <button
        type="button"
        onClick={reset}
        className="mt-4 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
      >
        Reintentar
      </button>
    </section>
  );
}
