"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { getAssessmentScore, getAssessmentMembers, ApiError } from "@/lib/api";
import type { QuickAssessmentScore } from "@/lib/types";
import {
  Loader2,
  RefreshCw,
  ArrowRight,
  Users,
  Clock,
  Copy,
  Check,
  Share2,
  MessageCircle,
} from "lucide-react";
import RadarChart from "./RadarChart";

const POLL_INTERVAL = 15_000; // 15 seconds
const READY_THRESHOLD = 3; // mínimo de respuestas para mostrar el radar

interface MemberInfo {
  id: string;
  name: string;
  role: string;
  email: string;
  token: string;
  submitted: boolean;
}

export default function ScorePage() {
  const params = useParams();
  const assessmentId = params.id as string;

  const [scoreData, setScoreData] = useState<QuickAssessmentScore | null>(null);
  const [members, setMembers] = useState<MemberInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      // `/score` siempre está disponible (endpoint público) y devuelve
      // responses_count + member_count. No existe `/progress` en backend:
      // derivamos el estado de espera desde los campos del score response.
      const [score, membersList] = await Promise.all([
        getAssessmentScore(assessmentId),
        getAssessmentMembers(assessmentId).catch(() => [] as MemberInfo[]),
      ]);
      setScoreData(score);
      setMembers(membersList);
      setError("");
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("No se pudo cargar el score. Reintentando...");
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  function interviewUrl(token: string): string {
    if (typeof window === "undefined") return "";
    return `${window.location.origin}/interview/${token}`;
  }

  async function copyLink(token: string) {
    const url = interviewUrl(token);
    try {
      await navigator.clipboard.writeText(url);
      setCopiedToken(token);
      setTimeout(() => setCopiedToken(null), 2000);
    } catch {
      // Fallback: seleccionar input
      const input = document.createElement("input");
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopiedToken(token);
      setTimeout(() => setCopiedToken(null), 2000);
    }
  }

  function whatsappLink(member: MemberInfo): string {
    const url = interviewUrl(member.token);
    const text = `Hola ${member.name}, te invito a participar en un diagnóstico rápido y anónimo sobre nuestra organización (5-10 min). Responde aquí: ${url}`;
    return `https://wa.me/?text=${encodeURIComponent(text)}`;
  }

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
      </div>
    );
  }

  if (error && !scoreData) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <h1 className="text-lg font-semibold text-gray-900">
            No pudimos cargar tu score
          </h1>
          <p className="mt-2 text-sm text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  const responsesCount = scoreData?.responses_count ?? 0;
  const isReady = responsesCount >= READY_THRESHOLD;
  const totalInvited = members.length || scoreData?.member_count || 0;
  const pendingMembers = members.filter((m) => !m.submitted);
  const completedMembers = members.filter((m) => m.submitted);

  // Waiting state — aún no hay suficientes respuestas de miembros
  if (!isReady) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-lg">
          <div className="text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-brand-50">
              <Clock className="h-8 w-8 text-brand-600" />
            </div>

            <h1 className="mt-6 text-xl font-bold text-gray-900">
              Esperando respuestas
            </h1>
            <p className="mt-2 text-sm text-gray-500">
              Tu score se generará automáticamente cuando al menos{" "}
              {READY_THRESHOLD} miembros respondan.
            </p>
          </div>

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
                {responsesCount} de {totalInvited}
              </span>
            </div>

            <div className="h-2 w-full rounded-full bg-gray-100">
              <div
                className="h-2 rounded-full bg-brand-600 transition-all duration-500"
                style={{
                  width: `${
                    totalInvited > 0
                      ? (responsesCount / totalInvited) * 100
                      : 0
                  }%`,
                }}
              />
            </div>

            {/* Individual dots */}
            <div className="mt-4 flex justify-center gap-2">
              {Array.from({ length: totalInvited }).map((_, i) => (
                <div
                  key={i}
                  className={`h-3 w-3 rounded-full transition-colors ${
                    i < responsesCount ? "bg-green-500" : "bg-gray-200"
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Member links — copiar y compartir. En esta versión no hay envío
              automático de email, así que el dueño comparte los links
              manualmente por WhatsApp o copiándolos. */}
          {pendingMembers.length > 0 && (
            <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-5">
              <div className="flex items-start gap-3">
                <Share2 className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h2 className="text-sm font-semibold text-amber-900">
                    Comparte los links con tu equipo
                  </h2>
                  <p className="mt-1 text-xs text-amber-800">
                    Cada miembro tiene un link único y anónimo. Compártelo por
                    WhatsApp, email o chat.
                  </p>
                </div>
              </div>

              <div className="mt-4 space-y-2">
                {pendingMembers.map((m) => (
                  <div
                    key={m.id}
                    className="rounded-lg border border-amber-200 bg-white p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {m.name || m.email}
                        </div>
                        {m.role && (
                          <div className="text-xs text-gray-500 truncate">
                            {m.role}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <button
                          onClick={() => copyLink(m.token)}
                          className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                          title="Copiar link"
                        >
                          {copiedToken === m.token ? (
                            <>
                              <Check className="h-3 w-3 text-green-600" />
                              Copiado
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3" />
                              Copiar
                            </>
                          )}
                        </button>
                        <a
                          href={whatsappLink(m)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 rounded-md bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-green-700"
                          title="Compartir por WhatsApp"
                        >
                          <MessageCircle className="h-3 w-3" />
                          WhatsApp
                        </a>
                      </div>
                    </div>
                    <div className="mt-2 truncate rounded bg-gray-50 px-2 py-1 font-mono text-[10px] text-gray-500">
                      {interviewUrl(m.token)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {completedMembers.length > 0 && (
            <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-green-800">
                <Check className="h-4 w-4" />
                <span className="font-medium">
                  {completedMembers.length} miembro
                  {completedMembers.length !== 1 ? "s" : ""} ya respondió
                </span>
              </div>
            </div>
          )}

          <div className="mt-4 flex items-center justify-center gap-2 text-xs text-gray-400">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Actualizando cada 15 segundos
          </div>
        </div>
      </div>
    );
  }

  // Score ready state — construir el map y labels a partir del response v2
  const scoresMap: Record<string, number> = {};
  const labelsMap: Record<string, string> = {};
  for (const d of scoreData!.dimensions) {
    scoresMap[d.dimension] = d.score;
    labelsMap[d.dimension] = d.label;
  }

  const sortedDims = [...scoreData!.dimensions].sort(
    (a, b) => a.score - b.score,
  );
  const lowestDim = sortedDims[0];

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg text-center">
        <h1 className="text-2xl font-bold text-gray-900">
          El score de tu organización
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          Basado en tu percepción y la de {scoreData!.member_count} miembros de
          tu equipo.
        </p>

        {/* Radar Chart */}
        <div className="mt-8">
          <RadarChart scores={scoresMap} labels={labelsMap} />
        </div>

        {/* Score breakdown */}
        <div className="mt-8 space-y-3">
          {[...scoreData!.dimensions]
            .sort((a, b) => b.score - a.score)
            .map((d) => (
              <div
                key={d.dimension}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
              >
                <span className="text-sm font-medium text-gray-700">
                  {d.label}
                </span>
                <div className="flex items-center gap-3">
                  <div className="h-2 w-24 rounded-full bg-gray-100">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        d.score >= 4
                          ? "bg-green-500"
                          : d.score >= 3
                            ? "bg-yellow-500"
                            : "bg-red-400"
                      }`}
                      style={{ width: `${(d.score / 5) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-semibold text-gray-900">
                    {d.score.toFixed(1)}
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
              <strong>{lowestDim.score.toFixed(1)}</strong> en{" "}
              <strong>{lowestDim.label}</strong>. Con el diagnóstico completo
              podrías entender por qué, identificar dónde está la fricción y
              recibir recomendaciones específicas.
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
