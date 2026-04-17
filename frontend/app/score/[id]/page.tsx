"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getAssessmentScore, getAssessmentMembers, getMe, ApiError } from "@/lib/api";
import type { QuickAssessmentScore } from "@/lib/types";
import RadarChart from "./RadarChart";
import MemberLinks from "./MemberLinks";
import { RefreshCw, ArrowUpRight } from "lucide-react";

const POLL_INTERVAL_MS = 15_000;

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
  const id = params.id as string;

  const [score, setScore] = useState<QuickAssessmentScore | null>(null);
  const [members, setMembers] = useState<MemberInfo[]>([]);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [scoreData, membersData] = await Promise.all([
        getAssessmentScore(id),
        getAssessmentMembers(id),
      ]);
      setScore(scoreData);
      setMembers(membersData);
      setError("");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Error al cargar los resultados.");
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    // Load user's org for canvas link
    getMe().then((u) => setOrgId(u.organization_id || null)).catch(() => {});
    loadData();
    intervalRef.current = setInterval(() => {
      loadData(true);
    }, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loadData]);

  useEffect(() => {
    if (score && score.responses_count >= 3 && intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [score]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-sm text-gray-500">Cargando resultados...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="text-center max-w-sm">
          <p className="text-sm text-red-600">{error}</p>
          <button
            onClick={() => loadData()}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className="w-4 h-4" />
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (!score) return null;

  const hasEnoughResponses = score.responses_count >= 3;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-12">
        <h1 className="text-2xl font-bold text-gray-900 text-center">
          {score.org_name}
        </h1>
        <p className="mt-2 text-sm text-gray-500 text-center">
          {score.responses_count} de {score.member_count} miembros han respondido
        </p>

        {!hasEnoughResponses ? (
          <>
            <div className="mt-8 p-6 bg-white border border-gray-200 rounded-xl text-center">
              <div className="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center mx-auto">
                <RefreshCw className="w-6 h-6 text-amber-500 animate-spin" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-gray-900">
                Esperando respuestas
              </h2>
              <p className="mt-2 text-sm text-gray-500 max-w-xs mx-auto">
                Necesitas al menos 3 respuestas para generar el score radar.
                Comparte los enlaces con tu equipo.
              </p>
              <p className="mt-3 text-xs text-gray-400">
                Actualizando cada 15 segundos...
              </p>
            </div>

            {members.length > 0 && (
              <MemberLinks members={members} />
            )}
          </>
        ) : (
          <>
            {/* Radar Chart */}
            <div className="mt-8 p-6 bg-white border border-gray-200 rounded-xl">
              <h2 className="text-base font-semibold text-gray-900 mb-4 text-center">
                Score Radar
              </h2>
              <RadarChart dimensions={score.dimensions} />
            </div>

            {/* Dimension details */}
            <div className="mt-6 space-y-3">
              {score.dimensions.map((dim) => {
                const pct = Math.round((dim.score / dim.max_score) * 100);
                return (
                  <div
                    key={dim.dimension}
                    className="p-4 bg-white border border-gray-200 rounded-xl"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900">
                        {dim.label}
                      </span>
                      <span className="text-sm font-semibold text-gray-900">
                        {dim.score.toFixed(1)} / {dim.max_score}
                      </span>
                    </div>
                    <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          pct >= 70
                            ? "bg-emerald-500"
                            : pct >= 40
                            ? "bg-amber-500"
                            : "bg-red-500"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Go to canvas */}
            {orgId && (
              <Link
                href={`/org/${orgId}/canvas`}
                className="mt-6 w-full inline-flex items-center justify-center gap-2 px-5 py-3 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800"
              >
                Ir al canvas organizacional
                <ArrowUpRight className="w-4 h-4" />
              </Link>
            )}

            {/* CTA Upgrade */}
            <div className="mt-4 p-6 bg-gray-100 rounded-xl text-center">
              <h3 className="text-base font-semibold text-gray-900">
                ¿Quieres un diagnóstico completo?
              </h3>
              <p className="mt-2 text-sm text-gray-500">
                Desbloquea 8 dimensiones, entrevistas profundas, motor de IA y
                diagnóstico narrativo con recomendaciones.
              </p>
              <button className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-white">
                Conocer plan Premium
                <ArrowUpRight className="w-4 h-4" />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
