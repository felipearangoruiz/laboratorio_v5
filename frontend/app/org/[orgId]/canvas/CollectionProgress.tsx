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
    <div className="h-10 border-b border-gray-200 bg-white flex items-center px-4 gap-3">
      <div className="flex items-center gap-2 text-xs text-gray-600">
        <span className="font-medium">
          {status.completed} de {status.total_members} entrevistas completadas
        </span>
        <span className="text-gray-400">({pct}%)</span>
      </div>

      {/* Mini progress bar */}
      <div className="w-32 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            status.threshold_met ? "bg-emerald-500" : "bg-blue-500"
          }`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>

      {/* Threshold indicator */}
      <div className="relative w-32 h-1.5">
        <div className="absolute left-[40%] -top-0.5 w-0.5 h-2.5 bg-gray-400 rounded" title="Umbral 40%" />
      </div>

      {status.threshold_met && (
        <div className="ml-auto flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-500" />
          <button className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium bg-emerald-50 text-emerald-700 rounded-full hover:bg-emerald-100">
            Genera tu diagnóstico
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
}
