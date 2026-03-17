import type { IntakePayload, Symptom } from "@/lib/types";
import { intakeSchema } from "@/lib/validation";
import type { ZodError } from "zod";

export type IntakeStepId =
  | "personal"
  | "metrics"
  | "medical"
  | "vitals"
  | "lifestyle"
  | "symptoms"
  | "assumption";

export const steps: { id: IntakeStepId; label: string }[] = [
  { id: "personal", label: "Personal Info" },
  { id: "metrics", label: "Body Metrics" },
  { id: "medical", label: "Medical Info" },
  { id: "vitals", label: "Vitals" },
  { id: "lifestyle", label: "Lifestyle" },
  { id: "symptoms", label: "Symptoms" },
  { id: "assumption", label: "Optional Assumption" }
];

export type IntakeState = {
  stepIndex: number;
  intake: IntakePayload;
  fieldErrors: Record<string, string>;
};

export type IntakeAction =
  | { type: "goNext" }
  | { type: "goBack" }
  | { type: "goTo"; index: number }
  | { type: "setField"; path: string; value: unknown }
  | { type: "addSymptom"; symptom?: Partial<Symptom> }
  | { type: "removeSymptom"; index: number }
  | { type: "setErrors"; errors: Record<string, string> }
  | { type: "clearErrors" }
  | { type: "reset" };

export const initialIntake: IntakePayload = {
  personalInfo: {
    fullName: "",
    dob: "",
    gender: "prefer_not_to_say",
    bloodGroup: ""
  },
  bodyMetrics: {
    heightCm: 170,
    weightKg: 70
  },
  medicalInfo: {
    conditions: "",
    allergies: "",
    medications: ""
  },
  vitals: {},
  lifestyle: {},
  symptoms: [
    { name: "", durationDays: 0, intensity: 3, frequencyPerDay: 1 }
  ],
  assumption: ""
};

export const initialState: IntakeState = {
  stepIndex: 0,
  intake: initialIntake,
  fieldErrors: {}
};

function setDeep(obj: any, path: string, value: unknown) {
  const parts = path.split(".");
  const copy = structuredClone(obj);
  let cur = copy;
  for (let i = 0; i < parts.length - 1; i++) {
    const key = parts[i]!;
    if (cur[key] == null || typeof cur[key] !== "object") cur[key] = {};
    cur = cur[key];
  }
  cur[parts[parts.length - 1]!] = value;
  return copy;
}

export function intakeReducer(state: IntakeState, action: IntakeAction): IntakeState {
  switch (action.type) {
    case "goNext":
      return {
        ...state,
        stepIndex: Math.min(steps.length - 1, state.stepIndex + 1),
        fieldErrors: {}
      };
    case "goBack":
      return {
        ...state,
        stepIndex: Math.max(0, state.stepIndex - 1),
        fieldErrors: {}
      };
    case "goTo":
      return {
        ...state,
        stepIndex: Math.max(0, Math.min(steps.length - 1, action.index)),
        fieldErrors: {}
      };
    case "setField":
      return {
        ...state,
        intake: setDeep(state.intake, action.path, action.value)
      };
    case "addSymptom": {
      const next: Symptom = {
        name: action.symptom?.name ?? "",
        durationDays: action.symptom?.durationDays ?? 0,
        intensity: (action.symptom?.intensity as any) ?? 3,
        frequencyPerDay: action.symptom?.frequencyPerDay ?? 1
      };
      return { ...state, intake: { ...state.intake, symptoms: [...state.intake.symptoms, next] } };
    }
    case "removeSymptom": {
      const next = state.intake.symptoms.filter((_, i) => i !== action.index);
      return { ...state, intake: { ...state.intake, symptoms: next.length ? next : state.intake.symptoms } };
    }
    case "setErrors":
      return { ...state, fieldErrors: action.errors };
    case "clearErrors":
      return { ...state, fieldErrors: {} };
    case "reset":
      return initialState;
    default:
      return state;
  }
}

export function validateStep(stepId: IntakeStepId, intake: IntakePayload) {
  const stepSchema = (() => {
    switch (stepId) {
      case "personal":
        return intakeSchema.pick({ personalInfo: true });
      case "metrics":
        return intakeSchema.pick({ bodyMetrics: true });
      case "medical":
        return intakeSchema.pick({ medicalInfo: true });
      case "vitals":
        return intakeSchema.pick({ vitals: true });
      case "lifestyle":
        return intakeSchema.pick({ lifestyle: true });
      case "symptoms":
        return intakeSchema.pick({ symptoms: true });
      case "assumption":
        return intakeSchema.pick({ assumption: true });
    }
  })();

  const res = stepSchema.safeParse(intake);
  if (res.success) return { ok: true as const, errors: {} as Record<string, string> };

  const zerr = res.error as ZodError;
  const errors: Record<string, string> = {};
  for (const issue of zerr.issues) {
    const path = issue.path.join(".");
    if (!errors[path]) errors[path] = issue.message;
  }
  return { ok: false as const, errors };
}

export function validateAll(intake: IntakePayload) {
  const res = intakeSchema.safeParse(intake);
  if (res.success) return { ok: true as const, errors: {} as Record<string, string> };
  const errors: Record<string, string> = {};
  for (const issue of res.error.issues) {
    const path = issue.path.join(".");
    if (!errors[path]) errors[path] = issue.message;
  }
  return { ok: false as const, errors };
}

