"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";

const LEADER_QUESTIONS = [
  {
    id: "lf01",
    dimension: "liderazgo",
    texto:
      "¿Qué tan claro es para tu equipo quién toma las decisiones importantes?",
    tipo: "likert",
  },
  {
    id: "lf02",
    dimension: "liderazgo",
    texto:
      "¿Qué tan accesible eres para tu equipo cuando necesitan resolver problemas?",
    tipo: "likert",
  },
  {
    id: "lf03",
    dimension: "comunicacion",
    texto:
      "¿Qué tan bien fluye la información entre las diferentes áreas o personas de tu organización?",
    tipo: "likert",
  },
  {
    id: "lf04",
    dimension: "comunicacion",
    texto:
      "¿Con qué frecuencia sientes que la información importante llega tarde o incompleta?",
    tipo: "likert",
  },
  {
    id: "lf05",
    dimension: "cultura",
    texto:
      "¿Qué tanto crees que los valores declarados de tu organización se practican en el día a día?",
    tipo: "likert",
  },
  {
    id: "lf06",
    dimension: "cultura",
    texto:
      "¿Qué tan cómoda se siente tu gente para expresar desacuerdos o ideas diferentes?",
    tipo: "likert",
  },
  {
    id: "lf07",
    dimension: "operacion",
    texto:
      "¿Qué tan eficientes son los procesos de trabajo en tu organización?",
    tipo: "likert",
  },
  {
    id: "lf08",
    dimension: "operacion",
    texto:
      "¿Con qué frecuencia se presentan cuellos de botella o bloqueos que retrasan el trabajo?",
    tipo: "likert",
  },
  {
    id: "lf09",
    dimension: "general",
    texto:
      "¿Cuál es el mayor desafío que enfrenta tu organización internamente en este momento?",
    tipo: "abierta",
  },
];

const DIMENSION_LABELS: Record<string, string> = {
  liderazgo: "Liderazgo",
  comunicacion: "Comunicación",
  cultura: "Cultura",
  operacion: "Operación",
  general: "General",
};

interface Props {
  responses: Record<string, number | string>;
  setResponses: (r: Record<string, number | string>) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function StepLeaderSurvey({
  responses,
  setResponses,
  onNext,
  onBack,
}: Props) {
  function setAnswer(id: string, value: number | string) {
    setResponses({ ...responses, [id]: value });
  }

  const likertQuestions = LEADER_QUESTIONS.filter((q) => q.tipo === "likert");
  const answeredLikert = likertQuestions.filter(
    (q) => responses[q.id] !== undefined,
  ).length;
  const allLikertAnswered = answeredLikert === likertQuestions.length;

  let currentDimension = "";

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900">Tu percepción</h2>
      <p className="mt-1 text-sm text-gray-500">
        Responde según tu experiencia como líder. No hay respuestas correctas.
      </p>
      <p className="mt-1 text-xs text-gray-400">
        {answeredLikert} de {likertQuestions.length} preguntas respondidas
      </p>

      <div className="mt-6 space-y-6">
        {LEADER_QUESTIONS.map((q) => {
          const showDimHeader = q.dimension !== currentDimension;
          if (showDimHeader) currentDimension = q.dimension;

          return (
            <div key={q.id}>
              {showDimHeader && (
                <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-brand-600">
                  {DIMENSION_LABELS[q.dimension]}
                </div>
              )}

              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <p className="text-sm text-gray-800">{q.texto}</p>

                {q.tipo === "likert" ? (
                  <div className="mt-3 flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((v) => (
                      <button
                        key={v}
                        type="button"
                        onClick={() => setAnswer(q.id, v)}
                        className={`flex h-10 w-10 items-center justify-center rounded-lg text-sm font-medium transition-colors ${
                          responses[q.id] === v
                            ? "bg-brand-600 text-white"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        }`}
                      >
                        {v}
                      </button>
                    ))}
                    <div className="ml-2 flex justify-between text-[10px] text-gray-400 w-full">
                      <span>Bajo</span>
                      <span>Alto</span>
                    </div>
                  </div>
                ) : (
                  <textarea
                    value={(responses[q.id] as string) ?? ""}
                    onChange={(e) => setAnswer(q.id, e.target.value)}
                    rows={3}
                    className="mt-3 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
                    placeholder="Escribe tu respuesta..."
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Atrás
        </button>
        <button
          onClick={onNext}
          disabled={!allLikertAnswered}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40 transition-colors"
        >
          Siguiente
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
