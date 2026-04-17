"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { Progress, ScoreResponse } from "@/lib/types";
import { Loader2, RefreshCw, ArrowRight, Users, Clock } from "lucide-react";
import RadarChart from "./RadarChart";

const POLL_INTERVAL = 15_000; // 15 seconds

const DIMENSION_LABELS: Record<string, string> = {
  liderazgo: "Liderazgo",
  comunicacion: "Comunicación",
  cultura: "Cultura",
  operacion: "Operación",
};

export default function ScorePage() {
  const params = useParams();
  const assessmentId = params.id as string;

  const [progress, setProgress] = useState<Progress | null>(null);
  const [scores, setScores] = useState<ScoreResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProgress = useCallback(async () => {
    try {
      const prog = await apiFetch<Progress>(
        `/quick-assessment/${assessmentId}/progress`,
      );
      setProgress(prog);

      if (prog.ready) {
        const scoreData = await apiFetch<ScoreResponse>(
          `/quick-assessment/${assessmentId}/score`,
        );
        setScores(scoreData);
      }
    } catch {
      // Silently retry on next poll
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    fetchProgress();
    const interval = setInterval(fetchProgress, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchProgress]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
      </div>
    );
  }

  // Waiting state
  if (!scores) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-4">
        <div className="w-full max-w-md text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-brand-50">
            <Clock className="h-8 w-8 text-brand-600" />
          </div>

          <h1 className="mt-6 text-xl font-bold text-gray-900">
            Esperando respuestas
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Tu score se generará automáticamente cuando al menos{" "}
            {progress?.threshold ?? 3} miembros respondan.
          </p>

          {/* Progress indicator */}
          <div className="mt-8 rounded-lg border border-gray-200 bg-white p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-700">
                  Respuestas
                </span>
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {progress?.total_completed ?? 0} de{" "}
                {progress?.total_invited ?? 0}
              </span>
            </div>

            <div className="h-2 w-full rounded-full bg-gray-100">
              <div
                className="h-2 rounded-full bg-brand-600 transition-all duration-500"
                style={{
                  width: `${
                    progress && progress.total_invited > 0
                      ? (progress.total_completed / progress.total_invited) *
                        100
                      : 0
                  }%`,
                }}
              />
            </div>

            {/* Individual dots */}
            <div className="mt-4 flex justify-center gap-2">
              {Array.from({ length: progress?.total_invited ?? 0 }).map(
                (_, i) => (
                  <div
                    key={i}
                    className={`h-3 w-3 rounded-full transition-colors ${
                      i < (progress?.total_completed ?? 0)
                        ? "bg-green-500"
                        : "bg-gray-200"
                    }`}
                  />
                ),
              )}
            </div>
          </div>

          <div className="mt-4 flex items-center justify-center gap-2 text-xs text-gray-400">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Actualizando cada 15 segundos
          </div>
        </div>
      </div>
    );
  }

  // Score ready state
  const lowestDim = Object.entries(scores.scores).sort(
    ([, a], [, b]) => a - b,
  )[0];

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg text-center">
        <h1 className="text-2xl font-bold text-gray-900">
          El score de tu organización
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          Basado en tu percepción y la de {scores.member_count} miembros de tu
          equipo.
        </p>

        {/* Radar Chart */}
        <div className="mt-8">
          <RadarChart scores={scores.scores} labels={DIMENSION_LABELS} />
        </div>

        {/* Score breakdown */}
        <div className="mt-8 space-y-3">
          {Object.entries(scores.scores)
            .sort(([, a], [, b]) => b - a)
            .map(([dim, score]) => (
              <div
                key={dim}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
              >
                <span className="text-sm font-medium text-gray-700">
                  {DIMENSION_LABELS[dim] ?? dim}
                </span>
                <div className="flex items-center gap-3">
                  <div className="h-2 w-24 rounded-full bg-gray-100">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        score >= 4
                          ? "bg-green-500"
                          : score >= 3
                            ? "bg-yellow-500"
                            : "bg-red-400"
                      }`}
                      style={{ width: `${(score / 5) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-semibold text-gray-900">
                    {score.toFixed(1)}
                  </span>
                </div>
              </div>
            ))}
        </div>

        {/* Contextual message */}
        {lowestDim && (
          <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-left">
            <p className="text-sm text-amber-800">
              Tu organización tiene un score de{" "}
              <strong>{lowestDim[1].toFixed(1)}</strong> en{" "}
              <strong>{DIMENSION_LABELS[lowestDim[0]]}</strong>. Con el
              diagnóstico completo podrías entender por qué, identificar dónde
              está la fricción y recibir recomendaciones específicas.
            </p>
          </div>
        )}

        {/* Upgrade CTA */}
        <div className="mt-8 rounded-lg border border-brand-200 bg-brand-50 p-6">
          <h3 className="text-base font-semibold text-gray-900">
            Desbloquea el diagnóstico completo
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            8 dimensiones, entrevistas profundas, motor de IA y recomendaciones
            accionables.
          </p>
          <button className="mt-4 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-6 py-3 text-sm font-medium text-white hover:bg-brand-700 transition-colors">
            Comenzar prueba premium
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
