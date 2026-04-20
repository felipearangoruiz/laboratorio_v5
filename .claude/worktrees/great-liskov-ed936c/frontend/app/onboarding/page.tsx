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
  const [leaderResponses, setLeaderResponses] = useState<Record<string, any>>({});
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

  const progressPct = Math.round(((step + 1) / TOTAL_STEPS) * 100);

  return (
    <div className="flex min-h-screen flex-col bg-warm-50">
      {/* Thin accent progress bar at very top */}
      <div className="fixed top-0 left-0 right-0 z-50 h-[2px] bg-warm-200">
        <div
          className="h-full bg-accent transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Logo strip */}
      <header className="border-b border-warm-200 bg-warm-50/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-lg items-center justify-between px-6 py-4">
          <span className="font-display italic text-lg text-warm-900">
            Laboratorio
          </span>
          <span className="text-xs text-warm-400">
            {step + 1} de {TOTAL_STEPS}
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="flex flex-1 flex-col items-center px-4 py-10">
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
    </div>
  );
}
