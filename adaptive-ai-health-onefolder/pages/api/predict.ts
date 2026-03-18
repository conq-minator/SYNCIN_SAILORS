import type { NextApiRequest, NextApiResponse } from "next";
import dbConnect from "@/lib/dbConnect";
import Disease from "@/models/Disease";
import { intakeSchema } from "@/lib/validation";
import type { PredictionCard } from "@/lib/types";

type DiseaseDoc = {
  _id: any;
  name: string;
  category: string;
  commonSymptoms: string[];
  riskLevel: 'low' | 'moderate' | 'high';
  summary: string;
  guidance?: string;
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") return res.status(405).json({ message: "Method not allowed" });

  try {
    await dbConnect();

    // Validate the incoming data from the Wizard
    const parsed = intakeSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json(parsed.error);

    const intake = parsed.data;
    const userSymptomList = intake.symptoms.map((s) => s.name.toLowerCase());

    // Pull all diseases from your MongoDB
    const dbDiseases = (await Disease.find({})) as DiseaseDoc[];

    const predictions: PredictionCard[] = dbDiseases.map((d: DiseaseDoc) => {
      // Logic: How many of the DB symptoms appear in the user's input?
      const matches = d.commonSymptoms.filter((s: string) => 
        userSymptomList.some(u => u.includes(s.toLowerCase()) || s.toLowerCase().includes(u))
      );

      const confidence = d.commonSymptoms.length > 0 
        ? Math.round((matches.length / d.commonSymptoms.length) * 100) 
        : 0;

      return {
        id: d._id.toString(),
        diseaseName: d.name,
        confidence: confidence,
        summary: d.summary,
        risk: d.riskLevel.toLowerCase() as "low" | "moderate" | "high", // Force lowercase to match ResultCard styles!
        details: {
          symptomsMatched: matches.length > 0 ? matches : ["Pattern Match"],
          supportingFactors: [`Category: ${d.category}`],
          contradictions: [],
          confidenceReasoning: "Confidence based on clinical symptom overlap.",
          guidance: d.guidance || "Consult a healthcare professional for persistent symptoms."
        }
      };
    })
    .filter((p: PredictionCard) => p.confidence > 15) // Only show relevant results
    .sort((a: PredictionCard, b: PredictionCard) => b.confidence - a.confidence);

    return res.status(200).json({ 
      predictions,
      meta: {
        generatedAt: new Date().toISOString(),
        confidenceExplanation: "Confidence calculated based on matching symptoms and clinical patterns.",
        disclaimer: "Assistive insights only. Not a substitute for professional medical advice."
      }
    });

  } catch (error) {
    console.error(error);
    return res.status(500).json({ message: "Internal Server Error" });
  }
}