"use client";

import { useState } from "react";

export type TreeNodeType = {
  id: string;
  name: string;
  description: string;
  nivel_jerarquico: number | null;
  tipo_nivel: string | null;
  is_default: boolean;
  member_count: number;
  children: TreeNodeType[];
};

type TreeNodeProps = {
  node: TreeNodeType;
};

export default function TreeNode({ node }: TreeNodeProps) {
  const hasChildren = node.children.length > 0;
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        {hasChildren ? (
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            aria-label={expanded ? `Contraer ${node.name}` : `Expandir ${node.name}`}
            className="mt-0.5 rounded-md p-1 text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <span className="text-sm leading-none">{expanded ? "▼" : "▶"}</span>
          </button>
        ) : (
          <span className="mt-0.5 inline-block h-7 w-7 shrink-0" aria-hidden="true" />
        )}

        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold text-slate-900">{node.name}</h3>
            {node.is_default ? (
              <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                Predeterminado
              </span>
            ) : null}
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
              {node.member_count} miembros
            </span>
          </div>

          {node.description ? <p className="text-sm text-slate-600">{node.description}</p> : null}

          {node.tipo_nivel ? (
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{node.tipo_nivel}</p>
          ) : null}
        </div>
      </div>

      {hasChildren && expanded ? (
        <div className="ml-6 space-y-3 border-l border-slate-200 pl-4">
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
