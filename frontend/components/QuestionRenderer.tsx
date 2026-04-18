"use client";

/**
 * QuestionRenderer — renderiza una pregunta del instrumento v2 con sus
 * capas condicionales (gradiente, numérica, ranking, etc.).
 *
 * Se reutiliza en el onboarding (gerente) y en la página de entrevista del
 * miembro (empleado + adaptativas).
 */

import type { V2Question, V2Layer } from "@/lib/types";

type ResponseValue =
  | number
  | string
  | string[]
  | Record<string, { frequency?: number; severity?: number }>
  | undefined;

export interface QuestionRendererProps {
  question: V2Question;
  responses: Record<string, any>;
  setResponse: (questionId: string, value: any) => void;
}

function isLayerActive(
  q: V2Question,
  layer: V2Layer,
  responses: Record<string, any>,
): boolean {
  const cond = layer.condition || {};
  if (cond.always) return true;

  const baseAnswer = responses[q.id];

  if (cond.base_answer_index_gte !== undefined) {
    if (
      typeof baseAnswer !== "number" ||
      baseAnswer < cond.base_answer_index_gte
    ) {
      return false;
    }
  }
  if (cond.base_answer_index_not !== undefined) {
    if (baseAnswer === cond.base_answer_index_not) return false;
  }
  if (cond.base_answer_index !== undefined) {
    if (baseAnswer !== cond.base_answer_index) return false;
  }
  if (cond.base_has_selections) {
    if (!Array.isArray(baseAnswer) || baseAnswer.length === 0) return false;
  }
  if (cond.base_excludes) {
    if (
      Array.isArray(baseAnswer) &&
      (cond.base_excludes as string[]).some((ex) => baseAnswer.includes(ex))
    ) {
      return false;
    }
  }
  if (cond.base_excludes_all) {
    // Se activa si ninguna de las opciones base_excludes_all está seleccionada
    if (Array.isArray(baseAnswer)) {
      return (cond.base_excludes_all as string[]).every(
        (ex) => !baseAnswer.includes(ex),
      );
    }
    return true;
  }
  if (cond.base_selection_count_gte) {
    if (
      !Array.isArray(baseAnswer) ||
      baseAnswer.length < cond.base_selection_count_gte
    ) {
      return false;
    }
  }

  return true;
}

function BaseInput({ question, responses, setResponse }: QuestionRendererProps) {
  const { base } = question;

  if (base.type === "single_select") {
    return (
      <div className="space-y-2">
        <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
        <div className="space-y-1.5">
          {base.options.map((opt, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setResponse(question.id, idx)}
              className={`w-full text-left px-4 py-2.5 text-sm rounded-lg border transition-colors ${
                responses[question.id] === idx
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
    const selected: string[] = Array.isArray(responses[question.id])
      ? (responses[question.id] as string[])
      : [];
    return (
      <div className="space-y-2">
        <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
        <p className="text-xs text-gray-400">
          Selecciona todas las que apliquen
        </p>
        <div className="flex flex-wrap gap-2">
          {base.options.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => {
                const updated = selected.includes(opt)
                  ? selected.filter((o) => o !== opt)
                  : [...selected, opt];
                setResponse(question.id, updated);
              }}
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

  if (base.type === "text_open" || base.type === "text_short") {
    return (
      <div className="space-y-2">
        <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
        <textarea
          value={(responses[question.id] as string) || ""}
          onChange={(e) => setResponse(question.id, e.target.value)}
          rows={base.type === "text_open" ? 4 : 2}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none resize-none"
          placeholder="Escribe tu respuesta..."
        />
      </div>
    );
  }

  if (base.type === "scale_1_5") {
    return (
      <div className="space-y-2">
        <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
        <div className="flex gap-1.5">
          {base.options.map((opt, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setResponse(question.id, idx)}
              className={`flex-1 py-2.5 text-xs rounded-lg border transition-colors ${
                responses[question.id] === idx
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

  if (base.type === "numeric_input") {
    const val = responses[question.id];
    return (
      <div className="space-y-2">
        <p className="text-sm text-gray-700 leading-relaxed">{base.text}</p>
        <input
          type="number"
          value={typeof val === "number" ? val : ""}
          onChange={(e) =>
            setResponse(
              question.id,
              e.target.value ? Number(e.target.value) : undefined,
            )
          }
          className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
          min={0}
        />
      </div>
    );
  }

  return null;
}

function LayerInput({
  question,
  layer,
  responses,
  setResponse,
}: {
  question: V2Question;
  layer: V2Layer;
  responses: Record<string, any>;
  setResponse: (id: string, value: any) => void;
}) {
  const layerId = layer.id;

  if (layer.type === "numeric_select" || layer.type === "single_select") {
    const options = layer.options || [];
    return (
      <div className="pl-4 border-l-2 border-gray-200 space-y-2">
        <p className="text-sm text-gray-600">{layer.text}</p>
        <div className="space-y-1.5">
          {options.map((opt, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setResponse(layerId, idx)}
              className={`w-full text-left px-4 py-2 text-sm rounded-lg border transition-colors ${
                responses[layerId] === idx
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

  if (layer.type === "text_short") {
    return (
      <div className="pl-4 border-l-2 border-gray-200 space-y-2">
        <p className="text-sm text-gray-600">{layer.text}</p>
        <textarea
          value={(responses[layerId] as string) || ""}
          onChange={(e) => setResponse(layerId, e.target.value)}
          rows={2}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none resize-none"
          placeholder="Escribe tu respuesta..."
        />
      </div>
    );
  }

  if (layer.type === "numeric_input") {
    const val = responses[layerId];
    return (
      <div className="pl-4 border-l-2 border-gray-200 space-y-2">
        <p className="text-sm text-gray-600">{layer.text}</p>
        <input
          type="number"
          value={typeof val === "number" ? val : ""}
          onChange={(e) =>
            setResponse(
              layerId,
              e.target.value ? Number(e.target.value) : undefined,
            )
          }
          className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none"
          min={0}
        />
      </div>
    );
  }

  if (layer.type === "gradient_per_selection") {
    const baseAnswer: string[] = Array.isArray(responses[question.id])
      ? (responses[question.id] as string[])
      : [];
    const excludes = (layer.condition?.base_excludes as string[]) || [];
    const items = baseAnswer.filter((a) => !excludes.includes(a));
    if (items.length === 0) return null;

    const gradientData: Record<
      string,
      { frequency?: number; severity?: number }
    > = responses[layerId] || {};

    return (
      <div className="pl-4 border-l-2 border-gray-200 space-y-4">
        <p className="text-sm text-gray-600 font-medium">{layer.text}</p>
        {items.map((item) => (
          <div key={item} className="space-y-2 bg-gray-50 rounded-lg p-3">
            <p className="text-sm font-medium text-gray-700">{item}</p>
            {layer.frequency_options && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Frecuencia:</p>
                <div className="flex flex-wrap gap-1.5">
                  {layer.frequency_options.map((opt, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        const updated = {
                          ...gradientData,
                          [item]: { ...gradientData[item], frequency: idx },
                        };
                        setResponse(layerId, updated);
                      }}
                      className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                        gradientData[item]?.frequency === idx
                          ? "bg-gray-900 text-white border-gray-900"
                          : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {layer.severity_options && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Severidad:</p>
                <div className="flex flex-wrap gap-1.5">
                  {layer.severity_options.map((opt, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        const updated = {
                          ...gradientData,
                          [item]: { ...gradientData[item], severity: idx },
                        };
                        setResponse(layerId, updated);
                      }}
                      className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                        gradientData[item]?.severity === idx
                          ? "bg-gray-900 text-white border-gray-900"
                          : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  if (
    layer.type === "ranking_from_selected" ||
    layer.type === "ranking_from_unselected"
  ) {
    const baseAnswer: string[] = Array.isArray(responses[question.id])
      ? (responses[question.id] as string[])
      : [];
    const allOptions = question.base.options;
    const pool =
      layer.type === "ranking_from_selected"
        ? baseAnswer
        : allOptions.filter((o) => !baseAnswer.includes(o));

    if (pool.length === 0) return null;

    const ranking: string[] = Array.isArray(responses[layerId])
      ? (responses[layerId] as string[])
      : [];
    const maxItems = layer.max_items || 1;

    return (
      <div className="pl-4 border-l-2 border-gray-200 space-y-2">
        <p className="text-sm text-gray-600">{layer.text}</p>
        <div className="space-y-1.5">
          {pool.map((opt) => {
            const idx = ranking.indexOf(opt);
            const isSelected = idx >= 0;
            return (
              <button
                key={opt}
                type="button"
                onClick={() => {
                  let updated: string[];
                  if (isSelected) {
                    updated = ranking.filter((r) => r !== opt);
                  } else if (ranking.length < maxItems) {
                    updated = [...ranking, opt];
                  } else {
                    return;
                  }
                  setResponse(layerId, updated);
                }}
                className={`w-full text-left px-4 py-2 text-sm rounded-lg border transition-colors ${
                  isSelected
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-700 border-gray-200 hover:border-gray-400"
                }`}
              >
                {isSelected ? `${idx + 1}. ` : ""}
                {opt}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  return null;
}

export default function QuestionRenderer({
  question,
  responses,
  setResponse,
}: QuestionRendererProps) {
  return (
    <div className="space-y-5">
      <BaseInput
        question={question}
        responses={responses}
        setResponse={setResponse}
      />
      {question.layers.map((layer) => {
        if (!isLayerActive(question, layer, responses)) return null;
        return (
          <LayerInput
            key={layer.id}
            question={question}
            layer={layer}
            responses={responses}
            setResponse={setResponse}
          />
        );
      })}
    </div>
  );
}

/**
 * Determina si una pregunta ha sido respondida en su capa base.
 * Útil para habilitar/deshabilitar el botón "Siguiente".
 */
export function isBaseAnswered(
  question: V2Question,
  responses: Record<string, any>,
): boolean {
  const v = responses[question.id];
  if (v === undefined || v === null) return false;
  const t = question.base.type;
  if (t === "multi_select") return Array.isArray(v) && v.length > 0;
  if (t === "text_open" || t === "text_short")
    return typeof v === "string" && v.trim().length > 0;
  if (
    t === "single_select" ||
    t === "numeric_select" ||
    t === "scale_1_5" ||
    t === "numeric_input"
  ) {
    return typeof v === "number";
  }
  return true;
}
