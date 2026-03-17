import { useMemo, useReducer, useState } from "react";
import { useRouter } from "next/router";
import { AnalyzingLoader } from "@/components/Loader/AnalyzingLoader";
import { ProgressBar } from "@/components/Form/ProgressBar";
import {
  initialState,
  intakeReducer,
  steps,
  validateAll,
  validateStep
} from "@/components/Form/intakeReducer";
import { postIntake, postPredict } from "@/lib/api";
import { saveSession } from "@/lib/storage";
import { PersonalStep } from "@/components/Form/steps/PersonalStep";
import { MetricsStep } from "@/components/Form/steps/MetricsStep";
import { MedicalStep } from "@/components/Form/steps/MedicalStep";
import { VitalsStep } from "@/components/Form/steps/VitalsStep";
import { LifestyleStep } from "@/components/Form/steps/LifestyleStep";
import { SymptomsStep } from "@/components/Form/steps/SymptomsStep";
import { AssumptionStep } from "@/components/Form/steps/AssumptionStep";

export function IntakeWizard() {
  const [state, dispatch] = useReducer(intakeReducer, initialState);
  const [submitting, setSubmitting] = useState(false);
  const [fatalError, setFatalError] = useState<string | null>(null);
  const router = useRouter();

  const step = steps[state.stepIndex]!;
  const stepId = step.id;

  const StepComponent = useMemo(() => {
    switch (stepId) {
      case "personal":
        return PersonalStep;
      case "metrics":
        return MetricsStep;
      case "medical":
        return MedicalStep;
      case "vitals":
        return VitalsStep;
      case "lifestyle":
        return LifestyleStep;
      case "symptoms":
        return SymptomsStep;
      case "assumption":
        return AssumptionStep;
    }
  }, [stepId]);

  async function onNext() {
    setFatalError(null);
    const v = validateStep(stepId, state.intake);
    if (!v.ok) {
      dispatch({ type: "setErrors", errors: v.errors });
      return;
    }
    dispatch({ type: "goNext" });
  }

  async function onSubmit() {
    setFatalError(null);
    const v = validateAll(state.intake);
    if (!v.ok) {
      dispatch({ type: "setErrors", errors: v.errors });
      const firstErrorStepIndex = steps.findIndex((s) =>
        Object.keys(v.errors).some((k) => k.startsWith(prefixForStep(s.id)))
      );
      if (firstErrorStepIndex >= 0) dispatch({ type: "goTo", index: firstErrorStepIndex });
      return;
    }

    setSubmitting(true);
    try {
      await postIntake(state.intake);
      const result = await postPredict(state.intake);

      saveSession({ intake: state.intake, result });
      await router.push("/results");
    } catch (e) {
      setFatalError(e instanceof Error ? e.message : "Unexpected error");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitting) return <AnalyzingLoader />;

  return (
    <div className="rounded-2xl border border-clinic-border bg-white p-6 shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-900">{step.label}</div>
          <div className="mt-1 text-xs text-slate-500">
            Step {state.stepIndex + 1} of {steps.length}
          </div>
        </div>
        <div className="w-full sm:max-w-xs">
          <ProgressBar current={state.stepIndex} total={steps.length} />
        </div>
      </div>

      {fatalError ? (
        <div className="mt-4 rounded-xl border border-red-200 bg-clinic-redSoft px-4 py-3 text-sm font-medium text-red-800">
          {fatalError}
        </div>
      ) : null}

      <div className="mt-6 transition-all">
        <StepComponent intake={state.intake} errors={state.fieldErrors} dispatch={dispatch} />
      </div>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          onClick={() => dispatch({ type: "goBack" })}
          disabled={state.stepIndex === 0}
          className="rounded-xl border border-clinic-border bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Back
        </button>

        {state.stepIndex < steps.length - 1 ? (
          <button
            type="button"
            onClick={onNext}
            className="rounded-xl bg-clinic-blue px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:opacity-95"
          >
            Continue
          </button>
        ) : (
          <button
            type="button"
            onClick={onSubmit}
            className="rounded-xl bg-clinic-green px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:opacity-95"
          >
            Submit for analysis
          </button>
        )}
      </div>
    </div>
  );
}

function prefixForStep(stepId: (typeof steps)[number]["id"]) {
  switch (stepId) {
    case "personal":
      return "personalInfo.";
    case "metrics":
      return "bodyMetrics.";
    case "medical":
      return "medicalInfo.";
    case "vitals":
      return "vitals.";
    case "lifestyle":
      return "lifestyle.";
    case "symptoms":
      return "symptoms";
    case "assumption":
      return "assumption";
  }
}

