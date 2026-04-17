"use client";

import { ArrowRight } from "lucide-react";

export default function StepWelcome({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center">
      <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
        <span className="text-2xl">🏢</span>
      </div>
      <h1 className="text-2xl font-bold text-gray-900">
        Bienvenido al diagnóstico
      </h1>
      <p className="mt-3 text-gray-600 leading-relaxed">
        En los próximos minutos vas a configurar un diagnóstico rápido de tu
        organización. Necesitarás:
      </p>
      <ul className="mt-6 space-y-3 text-left max-w-xs mx-auto">
        <li className="flex items-start gap-3 text-sm text-gray-700">
          <span className="mt-0.5 w-5 h-5 bg-gray-900 text-white rounded-full flex items-center justify-center text-xs flex-shrink-0">
            1
          </span>
          Información básica de tu organización
        </li>
        <li className="flex items-start gap-3 text-sm text-gray-700">
          <span className="mt-0.5 w-5 h-5 bg-gray-900 text-white rounded-full flex items-center justify-center text-xs flex-shrink-0">
            2
          </span>
          Responder una encuesta corta como líder (2 min)
        </li>
        <li className="flex items-start gap-3 text-sm text-gray-700">
          <span className="mt-0.5 w-5 h-5 bg-gray-900 text-white rounded-full flex items-center justify-center text-xs flex-shrink-0">
            3
          </span>
          Invitar a 3-5 miembros del equipo
        </li>
      </ul>
      <button
        onClick={onNext}
        className="mt-8 inline-flex items-center gap-2 px-6 py-3 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800"
      >
        Comenzar
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
