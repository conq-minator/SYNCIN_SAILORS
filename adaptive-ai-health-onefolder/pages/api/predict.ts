import type { NextApiRequest, NextApiResponse } from "next";
import { intakeSchema } from "@/lib/validation";
import type { PredictResponse, PredictionCard, RiskLevel } from "@/lib/types";

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ message: "Method not allowed" });
  }

  const parsed = intakeSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      message: "Invalid intake payload",
      details: parsed.error.flatten()
    });
  }

  const intake = parsed.data;
  const symptomNames = intake.symptoms
    .map((s) => s.name.trim().toLowerCase())
    .filter(Boolean);

  const features = {
    fever: symptomNames.some((s) => s.includes("fever")) || (intake.vitals.temperatureC ?? 0) >= 37.8,
    cough: symptomNames.some((s) => s.includes("cough")),
    soreThroat: symptomNames.some((s) => s.includes("throat")),
    fatigue: symptomNames.some((s) => s.includes("fatigue") || s.includes("tired")),
    headache: symptomNames.some((s) => s.includes("headache") || s.includes("migraine")),
    nausea: symptomNames.some((s) => s.includes("nausea") || s.includes("vomit")),
    diarrhea: symptomNames.some((s) => s.includes("diarrhea") || s.includes("loose stool")),
    chestPain: symptomNames.some((s) => s.includes("chest pain") || s.includes("chest")),
    shortBreath: symptomNames.some((s) => s.includes("breath") || s.includes("sob")),
    highSugar: (intake.vitals.bloodSugarMgDl ?? 0) >= 180,
    highBp:
      (intake.vitals.bpSystolic ?? 0) >= 140 ||
      (intake.vitals.bpDiastolic ?? 0) >= 90
  };

  const candidates: Array<{
    diseaseName: string;
    base: number;
    rules: Array<{ when: boolean; add: number; note: string }>;
    risk: RiskLevel;
    summary: string;
    guidance: string;
  }> = [
    {
      diseaseName: "Common Cold (Viral URTI)",
      base: 25,
      risk: "low",
      summary:
        "Upper respiratory symptoms often driven by viral infection; typically self-limited.",
      guidance:
        "Rest, hydration, and symptom relief. Seek care if symptoms worsen, persist >10 days, or breathing issues develop.",
      rules: [
        { when: features.cough, add: 10, note: "Cough reported" },
        { when: features.soreThroat, add: 10, note: "Sore throat reported" },
        { when: !features.fever, add: 5, note: "No significant fever present" }
      ]
    },
    {
      diseaseName: "Influenza-like Illness",
      base: 18,
      risk: "moderate",
      summary:
        "Flu-like presentations often include fever, fatigue, and respiratory symptoms.",
      guidance:
        "Monitor hydration and temperature. Consider testing during outbreaks and seek care for high fever, dehydration, or breathing difficulty.",
      rules: [
        { when: features.fever, add: 18, note: "Fever present" },
        { when: features.fatigue, add: 10, note: "Fatigue present" },
        { when: features.headache, add: 6, note: "Headache present" },
        { when: features.cough, add: 8, note: "Cough present" }
      ]
    },
    {
      diseaseName: "Gastroenteritis",
      base: 12,
      risk: "moderate",
      summary:
        "GI symptoms such as nausea/diarrhea may align with infectious gastroenteritis.",
      guidance:
        "Oral rehydration is key. Seek care for blood in stool, persistent vomiting, severe pain, or signs of dehydration.",
      rules: [
        { when: features.nausea, add: 12, note: "Nausea/vomiting reported" },
        { when: features.diarrhea, add: 18, note: "Diarrhea reported" },
        { when: features.fever, add: 5, note: "Fever supports infectious cause" }
      ]
    },
    {
      diseaseName: "Migraine / Primary Headache",
      base: 10,
      risk: "low",
      summary:
        "Recurrent headaches may be consistent with primary headache disorders depending on pattern and triggers.",
      guidance:
        "Track triggers and timing. Seek urgent care for sudden severe headache, neurologic symptoms, or head injury.",
      rules: [
        { when: features.headache, add: 25, note: "Headache is prominent" },
        { when: intake.lifestyle.stressLevel != null && intake.lifestyle.stressLevel >= 4, add: 8, note: "High stress level" },
        { when: intake.lifestyle.sleepHours != null && intake.lifestyle.sleepHours < 6, add: 6, note: "Reduced sleep" }
      ]
    },
    {
      diseaseName: "Hypertension (Possible)",
      base: 6,
      risk: "moderate",
      summary:
        "Elevated blood pressure values can indicate possible hypertension or acute elevation.",
      guidance:
        "Repeat measurements and consider clinical evaluation. Seek care for very high readings or symptoms like chest pain, severe headache, or shortness of breath.",
      rules: [
        { when: features.highBp, add: 30, note: "Elevated BP values reported" },
        { when: features.headache && features.highBp, add: 6, note: "Headache with high BP" }
      ]
    },
    {
      diseaseName: "Hyperglycemia (Possible)",
      base: 5,
      risk: "high",
      summary:
        "High blood sugar readings may indicate uncontrolled diabetes or acute hyperglycemia.",
      guidance:
        "If blood sugar is high repeatedly or accompanied by confusion, dehydration, vomiting, or rapid breathing, seek urgent care.",
      rules: [
        { when: features.highSugar, add: 35, note: "High blood sugar reading" }
      ]
    },
    {
      diseaseName: "Cardiorespiratory Concern (Needs Assessment)",
      base: 4,
      risk: "high",
      summary:
        "Chest pain or shortness of breath can be serious and warrants professional evaluation.",
      guidance:
        "If you have chest pain, shortness of breath, fainting, or severe weakness, seek urgent/emergency care immediately.",
      rules: [
        { when: features.chestPain, add: 35, note: "Chest pain reported" },
        { when: features.shortBreath, add: 35, note: "Shortness of breath reported" }
      ]
    }
  ];

  const assumption = (intake.assumption ?? "").trim().toLowerCase();
  if (assumption) {
    candidates.push({
      diseaseName: "User-stated assumption",
      base: 8,
      risk: "low",
      summary:
        "Your stated assumption is included for context and does not constitute a diagnosis.",
      guidance:
        "Use the detailed cards to compare supporting and contradicting factors. Consider professional evaluation for persistent or worsening symptoms.",
      rules: [{ when: true, add: 10, note: `User assumption: ${intake.assumption}` }]
    });
  }

  const cards: PredictionCard[] = candidates.map((c, idx) => {
    const matched = c.rules.filter((r) => r.when);
    const raw = c.base + matched.reduce((sum, r) => sum + r.add, 0);
    const confidence = clamp(raw, 3, 97);
    const contradictions: string[] = [];

    if (c.diseaseName.includes("Influenza") && !features.fever) {
      contradictions.push("No significant fever provided");
    }
    if (c.diseaseName.includes("Gastroenteritis") && !features.nausea && !features.diarrhea) {
      contradictions.push("GI symptoms not strongly represented");
    }

    const supporting = matched.map((m) => m.note);
    const symptomsMatched = intake.symptoms
      .map((s) => s.name.trim())
      .filter(Boolean)
      .slice(0, 8);

    return {
      id: `pred_${idx}_${Date.now()}`,
      diseaseName: c.diseaseName,
      confidence,
      summary: c.summary,
      risk: c.risk,
      details: {
        symptomsMatched: symptomsMatched.length ? symptomsMatched : ["No symptoms listed"],
        supportingFactors: supporting.length ? supporting : ["No strong supporting signals detected"],
        contradictions,
        confidenceReasoning:
          "Confidence is computed from pattern matches across symptoms, vitals, and context. More complete inputs can improve ranking stability.",
        guidance: c.guidance
      }
    };
  });

  const predictions = cards
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, clamp(intake.symptoms.length + 4, 5, 10));

  const response: PredictResponse = {
    predictions,
    meta: {
      generatedAt: new Date().toISOString(),
      confidenceExplanation: "Confidence reflects pattern matching with known data.",
      disclaimer:
        "This system provides assistive insights and does not replace medical diagnosis."
    }
  };

  return res.status(200).json(response);
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

