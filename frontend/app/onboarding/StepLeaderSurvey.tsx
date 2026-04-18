"use client";

import { useEffect, useState } from "react";
import { getLeaderQuestions, ApiError } from "@/lib/api";
import type { V2Question } from "@/lib/types";
import { Loader2, ChevronLeft, ChevronRight } from "lucide-react";
import QuestionRenderer, { isBaseAnswered } from "@/components/QuestionRenderer";

type ResponseValue = number | string | string[];

interface Props {
  responses: Record<string, ResponseValue>;
  setResponses: React.Dispatch<
    React.SetStateAction<Record<string, ResponseValue>>
  >;
  onNext: () => void;
  onBack: () => void;
}

export default function StepLeaderSurvey({
  responses,
  setResponses,
  onNext,
  onBack,
}: Props) {
  const [questions, setQuestions] = useState<V2Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [currentIdx, setCurrentIdx] = useState(0);

  useEffect(() => {
    getLeaderQuestions()
      .then((data) => {
        setQuestions(data.questions);
      })
      .catch((err) => {
        if (err instanceof ApiError) setError(err.message);
        else setError("No se pudieron cargar las preguntas.");
      })
      .finally(() => setLoading(false));
  }, []);

  function setResponse(questionId: string, value: any) {
    setResponses((prev) => ({ ...prev, [questionId]: value }));
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-red-600">{error}</p>
        <button
          onClick={onBack}
          className="mt-4 px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Volver
        </button>
      </div>
    );
  }

  const currentQ = questions[currentIdx];
  const isLast = currentIdx === questions.length - 1;
  const canAdvance = currentQ ? isBaseAnswered(currentQ, responses) : false;
  const progressPct =
    questions.length > 0
      ? Math.round(((currentIdx + 1) / questions.length) * 100)
      : 0;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900">
          Tu perspectiva como líder
        </h2>
        <p className="mt-2 text-sm text-gray-500">
          Responde desde tu experiencia. No hay respuestas correctas o
          incorrectas.
        </p>
      </div>

      {/* Mini progress bar intra-step */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
          <span>
            Pregunta {currentIdx + 1} de {questions.length}
          </span>
          <span>{progressPct}%</span>
        </div>
        <div className="h-1 w-full rounded-full bg-gray-200">
          <div
            className="h-1 rounded-full bg-brand-600 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {currentQ && (
        <div className="mb-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            {currentQ.title}
          </h3>
          <QuestionRenderer
            question={currentQ}
            responses={responses}
            setResponse={setResponse}
          />
        </div>
      )}

      <div className="mt-8 flex gap-3">
        {currentIdx === 0 ? (
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1 px-4 py-2.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <ChevronLeft className="h-4 w-4" />
            Atrás
          </button>
        ) : (
          <button
            onClick={() => setCurrentIdx((i) => i - 1)}
            className="inline-flex items-center gap-1 px-4 py-2.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <ChevronLeft className="h-4 w-4" />
            Anterior
          </button>
        )}
        {isLast ? (
          <button
            onClick={onNext}
            disabled={!canAdvance}
            className="flex-1 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
          >
            Continuar
          </button>
        ) : (
          <button
            onClick={() => setCurrentIdx((i) => i + 1)}
            disabled={!canAdvance}
            className="flex-1 inline-flex items-center justify-center gap-1 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
          >
            Siguiente
            <ChevronRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
