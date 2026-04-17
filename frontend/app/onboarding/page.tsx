"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import StepWelcome from "./StepWelcome";
import StepOrgInfo from "./StepOrgInfo";
import StepLeaderSurvey from "./StepLeaderSurvey";
import StepAddMembers from "./StepAddMembers";
import { createQuickAssessment, inviteMembers, ApiError } from "@/lib/api";
import type { QuickAssessmentMemberInvite } from "@/lib/types";

type Step = "welcome" | "org_info" | "leader_survey" | "add_members";

const STEPS: Step[] = ["welcome", "org_info", "leader_survey", "add_members"];

interface OrgData {
  org_name: string;
  org_type: string;
  size_range: string;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("welcome");
  const [orgData, setOrgData] = useState<OrgData>({
    org_name: "",
    org_type: "empresa",
    size_range: "1-10",
  });
  const [leaderResponses, setLeaderResponses] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const currentIndex = STEPS.indexOf(step);
  const progress = ((currentIndex + 1) / STEPS.length) * 100;

  function goNext() {
    const next = STEPS[currentIndex + 1];
    if (next) setStep(next);
  }

  function goBack() {
    const prev = STEPS[currentIndex - 1];
    if (prev) setStep(prev);
  }

  async function handleFinish(members: QuickAssessmentMemberInvite[]) {
    setError("");
    setLoading(true);
    try {
      const result = await createQuickAssessment({
        ...orgData,
        leader_responses: leaderResponses,
      });
      if (members.length > 0) {
        await inviteMembers(result.id, members);
      }
      // Go to score page — it has a link to canvas
      router.push(`/score/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Error al crear la evaluación. Intenta de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Progress bar */}
      <div className="h-1 bg-gray-200">
        <div
          className="h-1 bg-gray-900 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="max-w-lg mx-auto px-4 py-12">
        {error && (
          <div className="mb-6 p-3 text-sm text-red-700 bg-red-50 rounded-lg">
            {error}
          </div>
        )}

        {step === "welcome" && <StepWelcome onNext={goNext} />}

        {step === "org_info" && (
          <StepOrgInfo
            data={orgData}
            onChange={setOrgData}
            onNext={goNext}
            onBack={goBack}
          />
        )}

        {step === "leader_survey" && (
          <StepLeaderSurvey
            responses={leaderResponses}
            onChange={setLeaderResponses}
            onNext={goNext}
            onBack={goBack}
          />
        )}

        {step === "add_members" && (
          <StepAddMembers
            onFinish={handleFinish}
            onBack={goBack}
            loading={loading}
          />
        )}
      </div>
    </div>
  );
}
