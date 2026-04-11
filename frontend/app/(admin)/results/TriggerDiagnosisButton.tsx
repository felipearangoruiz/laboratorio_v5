"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/lib/apiFetch";

type TriggerDiagnosisButtonProps = {
  organizationId: string;
  disabled: boolean;
};

export default function TriggerDiagnosisButton({
  organizationId,
  disabled,
}: TriggerDiagnosisButtonProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setError(null);

    try {
      await apiFetch(`/organizations/${organizationId}/results/trigger`, {
        method: "POST",
      });

      startTransition(() => {
        router.refresh();
      });
    } catch (requestError) {
      if (requestError instanceof Error) {
        setError(requestError.message);
        return;
      }

      setError("No se pudo generar el diagnóstico.");
    }
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        disabled={disabled || isPending}
        onClick={handleClick}
        className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {isPending ? "Generando diagnóstico..." : "Generar diagnóstico"}
      </button>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
