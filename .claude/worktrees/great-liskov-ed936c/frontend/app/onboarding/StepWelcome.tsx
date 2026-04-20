"use client";

import { ArrowRight } from "lucide-react";

export default function StepWelcome({ onNext }: { onNext: () => void }) {
  return (
    <div>
      <h1 className="font-display italic text-3xl text-warm-900 leading-tight">
        Conoce cómo está tu organización
      </h1>
      <p className="mt-3 text-warm-500 leading-relaxed">
        En 10 minutos tendrás un score inicial en 4 dimensiones clave.
      </p>

      <div className="mt-8 space-y-3">
        {[
          {
            n: "1",
            title: "Tú respondes",
            body: "Una encuesta rápida sobre tu percepción (~5 min)",
          },
          {
            n: "2",
            title: "Tu equipo responde",
            body: "Invitas 3–5 miembros. Reciben un enlace anónimo.",
          },
          {
            n: "3",
            title: "Ves tu score",
            body: "Radar con 4 dimensiones: Liderazgo, Comunicación, Cultura y Operación.",
          },
        ].map((item) => (
          <div
            key={item.n}
            className="flex items-start gap-4 rounded-lg border border-warm-200 bg-white p-4 shadow-warm-sm"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/10 text-xs font-semibold text-accent">
              {item.n}
            </div>
            <div>
              <p className="text-sm font-semibold text-warm-900">{item.title}</p>
              <p className="mt-0.5 text-sm text-warm-500">{item.body}</p>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={onNext}
        className="mt-8 inline-flex items-center gap-2 rounded-md bg-accent px-6 py-3 text-sm font-semibold text-white hover:bg-accent-hover transition-colors"
      >
        Comenzar
        <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}
