"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import StepWelcome from "./StepWelcome";
import StepOrgInfo from "./StepOrgInfo";
import StepLeaderSurvey from "./StepLeaderSurvey";
import StepMembers from "./StepMembers";
import StepSending from "./StepSending";

export type OrgInfo = {
  name: string;
  type: string;
  size_range: string;
};

export type MemberEntry = {
  name: string;
  role_label: string;
  email: string;
};

const TOTAL_STEPS = 5;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);

  const [orgInfo, setOrgInfo] = useState<OrgInfo>({
    name: "",
    type: "",
    size_range: "",
  });
  // Respuestas del líder (v2 instrument completo):
  //   - single_select / numeric_select / scale_1_5: number (índice de opción)
  //   - multi_select / ranking: string[]
  //   - text_open / text_short: string
  //   - numeric_input: number (magnitud)
  //   - gradient_per_selection: { [item]: { frequency?: number, severity?: number } }
  const [leaderResponses, setLeaderResponses] = useState<Record<string, any>>(
    {},
  );
  const [members, setMembers] = useState<MemberEntry[]>([
    { name: "", role_label: "", email: "" },
    { name: "", role_label: "", email: "" },
    { name: "", role_label: "", email: "" },
  ]);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);

  function next() {
    setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
  }

  function back() {
    setStep((s) => Math.max(s - 1, 0));
  }

  function handleComplete(id: string) {
    router.push(`/score/${id}`);
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      {/* Progress bar */}
      <div className="mb-8 w-full max-w-lg">
        <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
          <span>Paso {step + 1} de {TOTAL_STEPS}</span>
          <span>{Math.round(((step + 1) / TOTAL_STEPS) * 100)}%</span>
        </div>
        <div className="h-1 w-full rounded-full bg-gray-200">
          <div
            className="h-1 rounded-full bg-brand-600 transition-all duration-300"
            style={{ width: `${((step + 1) / TOTAL_STEPS) * 100}%` }}
          />
        </div>
      </div>

      <div className="w-full max-w-lg">
        {step === 0 && <StepWelcome onNext={next} />}
        {step === 1 && (
          <StepOrgInfo
            orgInfo={orgInfo}
            setOrgInfo={setOrgInfo}
            onNext={next}
            onBack={back}
          />
        )}
        {step === 2 && (
          <StepLeaderSurvey
            responses={leaderResponses}
            setResponses={setLeaderResponses}
            onNext={next}
            onBack={back}
          />
        )}
        {step === 3 && (
          <StepMembers
            members={members}
            setMembers={setMembers}
            onNext={next}
            onBack={back}
          />
        )}
        {step === 4 && (
          <StepSending
            orgInfo={orgInfo}
            leaderResponses={leaderResponses}
            members={members}
            assessmentId={assessmentId}
            setAssessmentId={setAssessmentId}
            onComplete={handleComplete}
            onBack={back}
          />
        )}
      </div>
    </div>
  );
}
