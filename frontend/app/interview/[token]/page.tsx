"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  getPublicInterview,
  submitInterview,
  saveDraft,
  ApiError,
} from "@/lib/api";
import { FREE_DIMENSIONS } from "@/lib/types";
import type { PublicInterview } from "@/lib/types";
import { CheckCircle } from "lucide-react";

const LIKERT_OPTIONS = [
  { value: 1, label: "Muy en desacuerdo" },
  { value: 2, label: "En desacuerdo" },
  { value: 3, label: "Neutral" },
  { value: 4, label: "De acuerdo" },
  { value: 5, label: "Muy de acuerdo" },
];

export default function InterviewPage() {
  const params = useParams();
  const token = params.token as string;

  const [interview, setInterview] = useState<PublicInterview | null>(null);
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getPublicInterview(token);
        setInterview(data);
        if (data.data) {
          const numericData: Record<string, number> = {};
          for (const [k, v] of Object.entries(data.data)) {
            if (typeof v === "number") numericData[k] = v;
          }
          setResponses(numericData);
        }
        if (data.token_status === "COMPLETED") {
          setSubmitted(true);
        }
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("Error al cargar la entrevista.");
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  const autoSave = useCallback(
    async (data: Record<string, number>) => {
      try {
        await saveDraft(token, data);
      } catch {
        // silent fail on auto-save
      }
    },
    [token]
  );

  function setResponse(questionId: string, value: number) {
    const updated = { ...responses, [questionId]: value };
    setResponses(updated);
    autoSave(updated);
  }

  const allQuestions = FREE_DIMENSIONS.flatMap((d) => d.questions);
  const allAnswered = allQuestions.every((q) => responses[q.id] !== undefined);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await submitInterview(token, responses);
      setSubmitted(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Error al enviar respuestas.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    );
  }

  if (error && !interview) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="text-center max-w-sm">
          <h1 className="text-lg font-semibold text-gray-900">
            Enlace no válido
          </h1>
          <p className="mt-2 text-sm text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="text-center max-w-sm">
          <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto" />
          <h1 className="mt-4 text-xl font-bold text-gray-900">
            ¡Gracias por tu respuesta!
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Tu opinión ayudará a mejorar la organización. Puedes cerrar esta
            página.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-lg mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-xl font-bold text-gray-900">
            Encuesta organizacional
          </h1>
          {interview && (
            <p className="mt-1 text-sm text-gray-500">
              Hola {interview.name}. Esta encuesta es anónima y toma menos de 5
              minutos.
            </p>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-lg">
            {error}
          </div>
        )}

        {/* Questions */}
        <div className="space-y-8">
          {FREE_DIMENSIONS.map((dim) => (
            <div key={dim.id}>
              <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                {dim.label}
              </h2>
              <div className="mt-3 space-y-5">
                {dim.questions.map((q) => (
                  <div key={q.id}>
                    <p className="text-sm text-gray-700">{q.text}</p>
                    <div className="mt-2 flex gap-1">
                      {LIKERT_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() => setResponse(q.id, opt.value)}
                          className={`flex-1 py-2.5 text-xs rounded-md border transition-colors ${
                            responses[q.id] === opt.value
                              ? "bg-gray-900 text-white border-gray-900"
                              : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                          }`}
                          title={opt.label}
                        >
                          {opt.value}
                        </button>
                      ))}
                    </div>
                    <div className="flex justify-between mt-1">
                      <span className="text-[10px] text-gray-400">
                        Muy en desacuerdo
                      </span>
                      <span className="text-[10px] text-gray-400">
                        Muy de acuerdo
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Submit */}
        <div className="mt-8">
          <button
            onClick={handleSubmit}
            disabled={!allAnswered || submitting}
            className="w-full py-3 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
          >
            {submitting ? "Enviando..." : "Enviar respuestas"}
          </button>
          {!allAnswered && (
            <p className="mt-2 text-xs text-gray-400 text-center">
              Responde todas las preguntas ({Object.keys(responses).length}/
              {allQuestions.length})
            </p>
          )}
          <p className="mt-3 text-xs text-gray-400 text-center">
            Tus respuestas se guardan automáticamente. Puedes cerrar y volver
            después.
          </p>
        </div>
      </div>
    </div>
  );
}
