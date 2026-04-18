"use client";

import { useEffect, useState } from "react";
import { getCollectionStatus } from "@/lib/api";
import { ArrowRight, CheckCircle } from "lucide-react";

interface Props {
  orgId: string;
  refreshKey: number;
}

export default function CollectionProgress({ orgId, refreshKey }: Props) {
  const [status, setStatus] = useState<{
    total_members: number;
    completed: number;
    threshold_percent: number;
    threshold_met: boolean;
  } | null>(null);

  useEffect(() => {
    getCollectionStatus(orgId)
      .then(setStatus)
      .catch(() => {});
  }, [orgId, refreshKey]);

  if (!status) return null;

  const pct = status.total_members > 0
    ? Math.round((status.completed / status.total_members) * 100)
    : 0;

  return (
    <div
      className="h-9 flex items-center px-4 gap-3 border-b text-xs"
      style={{
        background: "rgba(13,13,20,0.88)",
        backdropFilter: "blur(6px)",
        borderBottomColor: "rgba(255,255,255,0.06)",
      }}
    >
      <span className="text-white/60 font-medium">
        {status.completed} de {status.total_members} entrevistas
      </span>
      <span className="text-white/30">({pct}%)</span>

      {/* Progress track */}
      <div className="w-28 h-1 bg-white/10 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            status.threshold_met ? "bg-emerald-500" : "bg-[#C2410C]"
          }`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>

      {/* 40% threshold marker */}
      <div className="relative w-28 h-1">
        <div
          className="absolute -top-1 w-px h-3 bg-white/25 rounded"
          style={{ left: "40%" }}
          title="Umbral 40%"
        />
      </div>

      {status.threshold_met && (
        <div className="ml-auto flex items-center gap-2">
          <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
          <button className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium bg-white/8 text-white/70 rounded hover:bg-white/12 transition-colors">
            Genera diagnóstico
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
}
