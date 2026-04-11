"use client";

import { useState, useTransition } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/lib/apiFetch";
import type { OrganizationStrategicContext } from "@/lib/types";

type StrategicContextFormProps = {
  organizationId: string;
  initialValue: OrganizationStrategicContext;
};

type FormState = {
  strategic_objectives: string;
  strategic_concerns: string;
  key_questions: string;
  additional_context: string;
};

const EMPTY_MESSAGE = "Agregar este contexto mejora la calidad del diagnóstico y hace más útil la lectura.";

export default function StrategicContextForm({
  organizationId,
  initialValue,
}: StrategicContextFormProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>({
    strategic_objectives: initialValue.strategic_objectives,
    strategic_concerns: initialValue.strategic_concerns,
    key_questions: initialValue.key_questions,
    additional_context: initialValue.additional_context,
  });

  function updateField(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    try {
      await apiFetch(`/organizations/${organizationId}`, {
        method: "PATCH",
        body: JSON.stringify(form),
      });

      setSuccess("Contexto estratégico guardado.");
      startTransition(() => {
        router.refresh();
      });
    } catch (requestError) {
      if (requestError instanceof Error) {
        setError(requestError.message);
        return;
      }

      setError("No se pudo guardar el contexto estratégico.");
    }
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Contexto estratégico</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
            Registra qué quiere lograr el caso, qué preocupa al admin y qué preguntas debería ayudar
            a responder el diagnóstico.
          </p>
        </div>
        <span
          className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${
            initialValue.is_complete
              ? "bg-emerald-100 text-emerald-800"
              : "bg-amber-100 text-amber-800"
          }`}
        >
          {initialValue.is_complete ? "Contexto disponible" : "Contexto pendiente"}
        </span>
      </div>

      {!initialValue.is_complete ? (
        <p className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {EMPTY_MESSAGE}
        </p>
      ) : null}

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Objetivo del caso</span>
          <textarea
            value={form.strategic_objectives}
            onChange={(event) => updateField("strategic_objectives", event.target.value)}
            rows={3}
            className="mt-2 w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-900"
            placeholder="Qué quiere lograr el cliente o el admin con este proceso."
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Preocupaciones principales</span>
          <textarea
            value={form.strategic_concerns}
            onChange={(event) => updateField("strategic_concerns", event.target.value)}
            rows={3}
            className="mt-2 w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-900"
            placeholder="Qué riesgos, tensiones o síntomas quiere entender mejor."
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Preguntas clave</span>
          <textarea
            value={form.key_questions}
            onChange={(event) => updateField("key_questions", event.target.value)}
            rows={3}
            className="mt-2 w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-900"
            placeholder="Qué preguntas debería ayudar a responder el diagnóstico."
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Contexto adicional</span>
          <textarea
            value={form.additional_context}
            onChange={(event) => updateField("additional_context", event.target.value)}
            rows={4}
            className="mt-2 w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-900"
            placeholder="Cambios recientes, antecedentes, limitaciones o señales que haya que tener presentes."
          />
        </label>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={isPending}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isPending ? "Guardando..." : "Guardar contexto"}
          </button>
          {success ? <p className="text-sm text-emerald-700">{success}</p> : null}
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
      </form>
    </section>
  );
}
