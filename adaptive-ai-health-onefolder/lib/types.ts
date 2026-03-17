export type Gender = "female" | "male" | "other" | "prefer_not_to_say";

export type Symptom = {
  name: string;
  durationDays: number;
  intensity: 1 | 2 | 3 | 4 | 5;
  frequencyPerDay: number;
};

export type IntakePayload = {
  personalInfo: {
    fullName: string;
    dob: string; // yyyy-mm-dd
    gender: Gender;
    bloodGroup: string;
  };
  bodyMetrics: {
    heightCm: number;
    weightKg: number;
  };
  medicalInfo: {
    conditions: string;
    allergies: string;
    medications: string;
  };
  vitals: {
    bpSystolic?: number;
    bpDiastolic?: number;
    bloodSugarMgDl?: number;
    heartRateBpm?: number;
    temperatureC?: number;
  };
  lifestyle: {
    sleepHours?: number;
    stressLevel?: 1 | 2 | 3 | 4 | 5;
    activityLevel?: "low" | "moderate" | "high";
  };
  symptoms: Symptom[];
  assumption?: string;
};

export type RiskLevel = "low" | "moderate" | "high";

export type PredictionCard = {
  id: string;
  diseaseName: string;
  confidence: number; // 0..100
  summary: string;
  risk: RiskLevel;
  details: {
    symptomsMatched: string[];
    supportingFactors: string[];
    contradictions: string[];
    confidenceReasoning: string;
    guidance: string;
  };
};

export type PredictResponse = {
  predictions: PredictionCard[];
  meta: {
    generatedAt: string;
    confidenceExplanation: string;
    disclaimer: string;
  };
};

