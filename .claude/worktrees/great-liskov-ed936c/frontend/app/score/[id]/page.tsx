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

const POLL_INTERVAL = 15_000;
const READY_THRESHOLD = 3;

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
    } catch {
      const input = document.createElement("input");
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
    }
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
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
      <div className="flex min-h-screen items-center justify-center bg-warm-50">
        <Loader2 className="h-6 w-6 animate-spin text-accent" />
      </div>
    );
  }

  if (error && !scoreData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-warm-50 px-4">
        <div className="text-center max-w-sm">
          <h1 className="font-display italic text-xl text-warm-900">No pudimos cargar tu score</h1>
          <p className="mt-2 text-sm text-warm-500">{error}</p>
        </div>
      </div>
    );
  }

  const responsesCount = scoreData?.responses_count ?? 0;
  const isReady = responsesCount >= READY_THRESHOLD;
  const totalInvited = members.length || scoreData?.member_count || 0;
  const pendingMembers = members.filter((m) => !m.submitted);
  const completedMembers = members.filter((m) => m.submitted);

  // ── Waiting state ──────────────────────────────────────
  if (!isReady) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-warm-50 px-4 py-12">
        <div className="w-full max-w-lg">
          <div className="text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-accent/10">
              <Clock className="h-7 w-7 text-accent" />
            </div>
            <h1 className="mt-5 font-display italic text-2xl text-warm-900">
              Esperando respuestas
            </h1>
            <p className="mt-2 text-sm text-warm-500 leading-relaxed">
              Tu score se generará automáticamente cuando al menos{" "}
              <strong className="text-warm-900">{READY_THRESHOLD}</strong> miembros respondan.
            </p>
          </div>

          {/* Progress card */}
          <div className="mt-8 rounded-lg border border-warm-200 bg-white p-6 shadow-warm-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-warm-400" />
                <span className="text-sm font-medium text-warm-700">Respuestas recibidas</span>
              </div>
              <span className="text-sm font-semibold text-warm-900">
                {responsesCount} de {totalInvited}
              </span>
            </div>

            <div className="h-1.5 w-full rounded-full bg-warm-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-accent transition-all duration-500"
                style={{ width: `${totalInvited > 0 ? (responsesCount / totalInvited) * 100 : 0}%` }}
              />
            </div>

            {/* Dots */}
            <div className="mt-4 flex justify-center gap-2">
              {Array.from({ length: totalInvited }).map((_, i) => (
                <div
                  key={i}
                  className={`h-2.5 w-2.5 rounded-full transition-colors ${
                    i < responsesCount ? "bg-accent" : "bg-warm-200"
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Pending member links */}
          {pendingMembers.length > 0 && (
            <div className="mt-5 rounded-lg border border-warm-200 bg-white p-5 shadow-warm-sm">
              <div className="flex items-start gap-3 mb-4">
                <Share2 className="h-4 w-4 text-accent flex-shrink-0 mt-0.5" />
                <div>
                  <h2 className="text-sm font-semibold text-warm-900">
                    Comparte los links con tu equipo
                  </h2>
                  <p className="mt-0.5 text-xs text-warm-500">
                    Cada miembro tiene un link único y anónimo.
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                {pendingMembers.map((m) => (
                  <div key={m.id} className="rounded-md border border-warm-200 bg-warm-50 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-warm-900 truncate">
                          {m.name || m.email}
                        </div>
                        {m.role && (
                          <div className="text-xs text-warm-500 truncate">{m.role}</div>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <button
                          onClick={() => copyLink(m.token)}
                          className="inline-flex items-center gap-1 rounded-md border border-warm-300 bg-white px-2.5 py-1.5 text-xs font-medium text-warm-700 hover:bg-warm-50 transition-colors"
                        >
                          {copiedToken === m.token ? (
                            <><Check className="h-3 w-3 text-success" /> Copiado</>
                          ) : (
                            <><Copy className="h-3 w-3" /> Copiar</>
                          )}
                        </button>
                        <a
                          href={whatsappLink(m)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 rounded-md bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-green-700 transition-colors"
                        >
                          <MessageCircle className="h-3 w-3" />
                          WhatsApp
                        </a>
                      </div>
                    </div>
                    <div className="mt-2 truncate rounded bg-warm-100 px-2 py-1 font-mono text-[10px] text-warm-500">
                      {interviewUrl(m.token)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {completedMembers.length > 0 && (
            <div className="mt-4 rounded-md border border-green-200 bg-green-50 px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-green-800">
                <Check className="h-4 w-4" />
                <span className="font-medium">
                  {completedMembers.length} miembro{completedMembers.length !== 1 ? "s" : ""} ya respondió
                </span>
              </div>
            </div>
          )}

          <div className="mt-5 flex items-center justify-center gap-2 text-xs text-warm-400">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Actualizando cada 15 segundos
          </div>
        </div>
      </div>
    );
  }

  // ── Score ready ────────────────────────────────────────
  const scoresMap: Record<string, number> = {};
  const labelsMap: Record<string, string> = {};
  for (const d of scoreData!.dimensions) {
    scoresMap[d.dimension] = d.score;
    labelsMap[d.dimension] = d.label;
  }

  const sortedDims = [...scoreData!.dimensions].sort((a, b) => a.score - b.score);
  const lowestDim = sortedDims[0];

  return (
    <div className="flex min-h-screen flex-col items-center bg-warm-50 px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Title */}
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-accent mb-3">
            Diagnóstico rápido
          </p>
          <h1 className="font-display italic text-3xl text-warm-900">
            El score de tu organización
          </h1>
          <p className="mt-2 text-sm text-warm-500">
            Basado en tu percepción y la de {scoreData!.member_count} miembros de tu equipo.
          </p>
        </div>

        {/* Radar */}
        <div className="mt-8 rounded-lg border border-warm-200 bg-white p-4 shadow-warm-sm">
          <RadarChart scores={scoresMap} labels={labelsMap} />
        </div>

        {/* Dimension bars */}
        <div className="mt-5 rounded-lg border border-warm-200 bg-white shadow-warm-sm overflow-hidden">
          {[...scoreData!.dimensions]
            .sort((a, b) => b.score - a.score)
            .map((d, i) => (
              <div
                key={d.dimension}
                className={`flex items-center justify-between px-5 py-3.5 gap-4 ${
                  i < scoreData!.dimensions.length - 1 ? "border-b border-warm-100" : ""
                }`}
              >
                <span className="text-sm font-medium text-warm-700 min-w-0 flex-1 truncate">
                  {d.label}
                </span>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="h-1.5 w-24 rounded-full bg-warm-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent transition-all"
                      style={{ width: `${(d.score / 5) * 100}%`, opacity: 0.4 + (d.score / 5) * 0.6 }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-semibold text-warm-900 font-mono">
                    {d.score.toFixed(1)}
                  </span>
                </div>
              </div>
            ))}
        </div>

        {/* Contextual insight */}
        {lowestDim && (
          <div className="mt-5 rounded-lg border border-warm-200 bg-white p-5 shadow-warm-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-warm-400 mb-2">
              Oportunidad de mejora
            </p>
            <p className="text-sm text-warm-700 leading-relaxed">
              Tu organización tiene un score de{" "}
              <strong className="text-warm-900">{lowestDim.score.toFixed(1)}</strong> en{" "}
              <strong className="text-warm-900">{lowestDim.label}</strong>. Con el diagnóstico
              completo podrías entender por qué, identificar dónde está la fricción y recibir
              recomendaciones específicas.
            </p>
          </div>
        )}

        {/* Upgrade CTA */}
        <div className="mt-5 rounded-lg p-6 text-center" style={{ background: "#0D0D14" }}>
          <p className="text-xs font-semibold uppercase tracking-wide text-white/40 mb-2">
            Plan premium
          </p>
          <h3 className="font-display italic text-xl text-white">
            Desbloquea el diagnóstico completo
          </h3>
          <p className="mt-2 text-sm text-white/50 leading-relaxed">
            8 dimensiones, entrevistas profundas, motor de IA y recomendaciones accionables.
          </p>
          <a
            href="/register"
            className="mt-5 inline-flex items-center gap-2 rounded-md bg-accent px-6 py-3 text-sm font-semibold text-white hover:bg-accent-hover transition-colors"
          >
            Comenzar prueba premium
            <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </div>
    </div>
  );
}
