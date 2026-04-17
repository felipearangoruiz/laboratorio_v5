"use client";

import { ArrowRight, BarChart3, Clock, Users } from "lucide-react";

export default function StepWelcome({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center">
      <h1 className="text-2xl font-bold text-gray-900">
        Conoce cómo está tu organización
      </h1>
      <p className="mt-2 text-gray-500">
        En 10 minutos tendrás un score inicial de tu organización en 4
        dimensiones clave.
      </p>

      <div className="mt-10 space-y-4 text-left">
        <div className="flex items-start gap-4 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-50 text-sm font-semibold text-brand-600">
            1
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">Tú respondes</p>
            <p className="text-sm text-gray-500">
              Una encuesta rápida sobre tu percepción (~5 min)
            </p>
          </div>
        </div>

        <div className="flex items-start gap-4 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-50 text-sm font-semibold text-brand-600">
            2
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">
              Tu equipo responde
            </p>
            <p className="text-sm text-gray-500">
              Invitas 3-5 miembros. Reciben un enlace por correo.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-4 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-50 text-sm font-semibold text-brand-600">
            3
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">Ves tu score</p>
            <p className="text-sm text-gray-500">
              Un radar con 4 dimensiones: Liderazgo, Comunicación, Cultura y
              Operación.
            </p>
          </div>
        </div>
      </div>

      <button
        onClick={onNext}
        className="mt-8 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-6 py-3 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
      >
        Comenzar
        <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}
