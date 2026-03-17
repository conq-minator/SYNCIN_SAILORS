import { z } from "zod";

export const symptomSchema = z.object({
  name: z.string().trim().min(2, "Symptom name is required"),
  durationDays: z.coerce.number().int().min(0, "Duration must be >= 0").max(3650),
  intensity: z.coerce
    .number()
    .int()
    .min(1, "Intensity must be 1–5")
    .max(5, "Intensity must be 1–5"),
  frequencyPerDay: z.coerce
    .number()
    .int()
    .min(0, "Frequency must be >= 0")
    .max(100)
});

export const intakeSchema = z.object({
  personalInfo: z.object({
    fullName: z.string().trim().min(2, "Full name is required"),
    dob: z
      .string()
      .trim()
      .regex(/^\d{4}-\d{2}-\d{2}$/, "DOB must be YYYY-MM-DD"),
    gender: z.enum(["female", "male", "other", "prefer_not_to_say"]),
    bloodGroup: z.string().trim().min(1, "Blood group is required")
  }),
  bodyMetrics: z.object({
    heightCm: z.coerce.number().min(30).max(250),
    weightKg: z.coerce.number().min(2).max(350)
  }),
  medicalInfo: z.object({
    conditions: z.string().trim().optional().default(""),
    allergies: z.string().trim().optional().default(""),
    medications: z.string().trim().optional().default("")
  }),
  vitals: z.object({
    bpSystolic: z.coerce.number().optional(),
    bpDiastolic: z.coerce.number().optional(),
    bloodSugarMgDl: z.coerce.number().optional(),
    heartRateBpm: z.coerce.number().optional(),
    temperatureC: z.coerce.number().optional()
  }),
  lifestyle: z.object({
    sleepHours: z.coerce.number().optional(),
    stressLevel: z.coerce.number().int().min(1).max(5).optional(),
    activityLevel: z.enum(["low", "moderate", "high"]).optional()
  }),
  symptoms: z.array(symptomSchema).min(1, "Add at least one symptom"),
  assumption: z.string().trim().optional()
});

export type IntakeInput = z.input<typeof intakeSchema>;
export type IntakeOutput = z.output<typeof intakeSchema>;

