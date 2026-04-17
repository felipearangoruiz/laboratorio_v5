"use client";

import { useState } from "react";
import { Check, Copy, CircleCheck, Clock } from "lucide-react";

interface MemberInfo {
  id: string;
  name: string;
  role: string;
  email: string;
  token: string;
  submitted: boolean;
}

export default function MemberLinks({ members }: { members: MemberInfo[] }) {
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  function getInterviewUrl(token: string) {
    if (typeof window !== "undefined") {
      return `${window.location.origin}/interview/${token}`;
    }
    return `/interview/${token}`;
  }

  async function copyLink(token: string) {
    const url = getInterviewUrl(token);
    await navigator.clipboard.writeText(url);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  }

  return (
    <div className="mt-6 p-4 bg-white border border-gray-200 rounded-xl">
      <h3 className="text-sm font-semibold text-gray-900">
        Enlaces de encuesta
      </h3>
      <p className="mt-1 text-xs text-gray-500">
        Comparte cada enlace con el miembro correspondiente.
      </p>
      <div className="mt-3 space-y-2">
        {members.map((m) => (
          <div
            key={m.id}
            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
          >
            <div className="flex items-center gap-2 min-w-0">
              {m.submitted ? (
                <CircleCheck className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              ) : (
                <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
              )}
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {m.name}
                </p>
                <p className="text-xs text-gray-500 truncate">{m.email}</p>
              </div>
            </div>
            {m.submitted ? (
              <span className="text-xs text-emerald-600 font-medium flex-shrink-0">
                Completada
              </span>
            ) : (
              <button
                onClick={() => copyLink(m.token)}
                className="flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 text-xs text-gray-700 border border-gray-200 rounded-md hover:bg-white"
              >
                {copiedToken === m.token ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-500" />
                    Copiado
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    Copiar enlace
                  </>
                )}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
