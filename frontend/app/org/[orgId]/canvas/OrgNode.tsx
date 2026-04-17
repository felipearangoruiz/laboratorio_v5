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
}

function OrgNode({ data, selected }: NodeProps<OrgNodeData>) {
  return (
    <div
      className={`px-4 py-3 bg-white border-2 rounded-xl shadow-sm min-w-[160px] transition-colors ${
        selected ? "border-gray-900 shadow-md" : "border-gray-200 hover:border-gray-400"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />

      <div className="text-sm font-semibold text-gray-900 truncate">
        {data.label}
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
