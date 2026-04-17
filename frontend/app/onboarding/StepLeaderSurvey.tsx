"use client";

import { FREE_DIMENSIONS } from "@/lib/types";

interface Props {
  responses: Record<string, number>;
  onChange: (responses: Record<string, number>) => void;
  onNext: () => void;
  onBack: () => void;
}

const LIKERT_OPTIONS = [
  { value: 1, label: "Muy en desacuerdo" },
  { value: 2, label: "En desacuerdo" },
  { value: 3, label: "Neutral" },
  { value: 4, label: "De acuerdo" },
  { value: 5, label: "Muy de acuerdo" },
];

export default function StepLeaderSurvey({
  responses,
  onChange,
  onNext,
  onBack,
}: Props) {
  const allQuestions = FREE_DIMENSIONS.flatMap((d) => d.questions);
  const allAnswered = allQuestions.every((q) => responses[q.id] !== undefined);

  function setResponse(questionId: string, value: number) {
    onChange({ ...responses, [questionId]: value });
  }

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900">
        Tu perspectiva como líder
      </h2>
      <p className="mt-2 text-sm text-gray-500">
        Evalúa cada afirmación según tu experiencia. No hay respuestas correctas
        o incorrectas.
      </p>

      <div className="mt-6 space-y-8">
        {FREE_DIMENSIONS.map((dim) => (
          <div key={dim.id}>
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
              {dim.label}
            </h3>
            <div className="mt-3 space-y-5">
              {dim.questions.map((q) => (
                <div key={q.id}>
                  <p className="text-sm text-gray-700">{q.text}</p>
                  <div className="mt-2 flex gap-1">
                    {LIKERT_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setResponse(q.id, opt.value)}
                        className={`flex-1 py-2 text-xs rounded-md border transition-colors ${
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
                    <span className="text-[10px] text-gray-400">Muy en desacuerdo</span>
                    <span className="text-[10px] text-gray-400">Muy de acuerdo</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 flex gap-3">
        <button
          onClick={onBack}
          className="px-4 py-2.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Atrás
        </button>
        <button
          onClick={onNext}
          disabled={!allAnswered}
          className="flex-1 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
        >
          Continuar
        </button>
      </div>

      {!allAnswered && (
        <p className="mt-2 text-xs text-gray-400 text-center">
          Responde todas las preguntas para continuar ({Object.keys(responses).length}/{allQuestions.length})
        </p>
      )}
    </div>
  );
}
