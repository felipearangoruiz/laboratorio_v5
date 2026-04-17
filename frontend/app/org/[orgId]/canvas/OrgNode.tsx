"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { Users } from "lucide-react";

interface OrgNodeData {
  label: string;
  area: string;
  role: string;
  memberCount: number;
  level: number | null;
  interviewStatus?: "none" | "invited" | "in_progress" | "completed" | "expired";
  activeLayer?: string;
}

const STATUS_STYLES: Record<string, string> = {
  none: "border-gray-200",
  invited: "border-blue-400 border-dashed",
  in_progress: "border-blue-500",
  completed: "border-emerald-500",
  expired: "border-orange-400",
};

const STATUS_DOT: Record<string, string> = {
  invited: "bg-blue-400",
  in_progress: "bg-blue-500 animate-pulse",
  completed: "bg-emerald-500",
  expired: "bg-orange-400",
};

function OrgNode({ data, selected }: NodeProps<OrgNodeData>) {
  const showStatus = data.activeLayer === "recoleccion";
  const status = data.interviewStatus || "none";
  const borderClass = showStatus ? STATUS_STYLES[status] : "border-gray-200";

  return (
    <div
      className={`px-4 py-3 bg-white border-2 rounded-xl shadow-sm min-w-[160px] transition-colors ${
        selected ? "border-gray-900 shadow-md" : borderClass + " hover:border-gray-400"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />

      <div className="flex items-center gap-2">
        <div className="text-sm font-semibold text-gray-900 truncate flex-1">
          {data.label}
        </div>
        {showStatus && status !== "none" && (
          <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${STATUS_DOT[status]}`} />
        )}
      </div>

      {data.role && (
        <div className="text-xs text-gray-500 truncate mt-0.5">{data.role}</div>
      )}

      {data.area && (
        <div className="mt-1.5">
          <span className="inline-block px-2 py-0.5 text-[10px] font-medium bg-blue-50 text-blue-700 rounded-full">
            {data.area}
          </span>
        </div>
      )}

      {data.memberCount > 0 && (
        <div className="mt-1.5 flex items-center gap-1 text-xs text-gray-400">
          <Users className="w-3 h-3" />
          {data.memberCount}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />
    </div>
  );
}

export default memo(OrgNode);
