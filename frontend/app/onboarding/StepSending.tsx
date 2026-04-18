"use client";

import { useEffect, useState } from "react";
import type { MemberEntry, OrgInfo } from "./page";
import { ApiError, createQuickAssessment, inviteMembers } from "@/lib/api";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
} from "lucide-react";

interface Props {
  orgInfo: OrgInfo;
  leaderResponses: Record<string, number | string | string[]>;
  members: MemberEntry[];
  assessmentId: string | null;
  setAssessmentId: (id: string) => void;
  onComplete: (id: string) => void;
  onBack: () => void;
}

type SendState =
  | "idle"
  | "creating-assessment"
  | "inviting"
  | "done"
  | "error";

export default function StepSending({
  orgInfo,
  leaderResponses,
  members,
  assessmentId,
  setAssessmentId,
  onComplete,
  onBack,
}: Props) {
  const [state, setState] = useState<SendState>("idle");
  const [error, setError] = useState("");

  const validMembers = members.filter((m) => m.name.trim() && m.email.trim());

  useEffect(() => {
    if (state === "idle") {
      send();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function send() {
    try {
      // Step 1: Create anonymous quick assessment (no auth required)
      setState("creating-assessment");
      const assessment = await createQuickAssessment({
        org_name: orgInfo.name,
        org_type: orgInfo.type,
        size_range: orgInfo.size_range,
        leader_responses: leaderResponses,
      });
      setAssessmentId(assessment.id);

      // Step 2: Invite members (map role_label -> role for v2 backend)
      setState("inviting");
      await inviteMembers(
        assessment.id,
        validMembers.map((m) => ({
          name: m.name,
          role: m.role_label,
          email: m.email,
        })),
      );

      setState("done");

      // Small delay before redirecting
      setTimeout(() => onComplete(assessment.id), 1500);
    } catch (err) {
      setState("error");
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Error inesperado");
      }
    }
  }

  const steps = [
    { key: "creating-assessment", label: "Guardando tus respuestas..." },
    { key: "inviting", label: "Enviando invitaciones..." },
    { key: "done", label: "¡Listo!" },
  ];

  const currentIndex = steps.findIndex((s) => s.key === state);

  return (
    <div className="text-center">
      <h2 className="text-xl font-bold text-gray-900">
        {state === "error" ? "Hubo un problema" : "Enviando invitaciones"}
      </h2>

      {state === "error" ? (
        <div className="mt-6">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
            <AlertCircle className="h-6 w-6 text-red-500" />
          </div>
          <p className="mt-4 text-sm text-red-600">{error}</p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={onBack}
              className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="h-4 w-4" />
              Volver
            </button>
            <button
              onClick={() => {
                setError("");
                setState("idle");
                send();
              }}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              Reintentar
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-8 space-y-3">
          {steps.map((s, i) => {
            const isDone = i < currentIndex || state === "done";
            const isActive = s.key === state;

            return (
              <div
                key={s.key}
                className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
                  isDone
                    ? "border-green-200 bg-green-50"
                    : isActive
                      ? "border-brand-200 bg-brand-50"
                      : "border-gray-100 bg-gray-50"
                }`}
              >
                {isDone ? (
                  <Check className="h-5 w-5 text-green-500" />
                ) : isActive ? (
                  <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
                ) : (
                  <div className="h-5 w-5 rounded-full border-2 border-gray-200" />
                )}
                <span
                  className={`text-sm ${
                    isDone
                      ? "text-green-700"
                      : isActive
                        ? "text-brand-700 font-medium"
                        : "text-gray-400"
                  }`}
                >
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
