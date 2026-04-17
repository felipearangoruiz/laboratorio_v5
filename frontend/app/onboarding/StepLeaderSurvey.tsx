"use client";

import { FREE_LEADER_QUESTIONS, type V2Question } from "@/lib/types";

interface Props {
  responses: Record<string, any>;
  onChange: (responses: Record<string, any>) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function StepLeaderSurvey({
  responses,
  onChange,
  onNext,
  onBack,
}: Props) {
  const allAnswered = FREE_LEADER_QUESTIONS.every(
    (q) => responses[q.id] !== undefined
  );

  function setResponse(questionId: string, value: any) {
    onChange({ ...responses, [questionId]: value });
  }

  function toggleMultiSelect(questionId: string, option: string) {
    const current: string[] = responses[questionId] || [];
    const updated = current.includes(option)
      ? current.filter((o: string) => o !== option)
      : [...current, option];
    setResponse(questionId, updated);
  }

  function renderQuestion(q: V2Question) {
    const { base } = q;

    if (base.type === "single_select") {
      return (
        <div key={q.id} className="space-y-2">
          <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
          <div className="space-y-1.5">
            {base.options.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => setResponse(q.id, idx)}
                className={`w-full text-left px-4 py-2.5 text-sm rounded-lg border transition-colors ${
                  responses[q.id] === idx
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-700 border-gray-200 hover:border-gray-400"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (base.type === "multi_select") {
      const selected: string[] = responses[q.id] || [];
      return (
        <div key={q.id} className="space-y-2">
          <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
          <p className="text-xs text-gray-400">Selecciona todas las que apliquen</p>
          <div className="flex flex-wrap gap-2">
            {base.options.map((opt) => (
              <button
                key={opt}
                onClick={() => toggleMultiSelect(q.id, opt)}
                className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                  selected.includes(opt)
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }

    return null;
  }

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900">
        Tu perspectiva como líder
      </h2>
      <p className="mt-2 text-sm text-gray-500">
        Responde desde tu experiencia. No hay respuestas correctas o incorrectas.
      </p>

      <div className="mt-6 space-y-8">
        {FREE_LEADER_QUESTIONS.map((q) => (
          <div key={q.id}>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              {q.title}
            </h3>
            {renderQuestion(q)}
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
          Responde todas las preguntas para continuar (
          {Object.keys(responses).filter((k) => FREE_LEADER_QUESTIONS.some((q) => q.id === k)).length}/
          {FREE_LEADER_QUESTIONS.length})
        </p>
      )}
    </div>
  );
}
