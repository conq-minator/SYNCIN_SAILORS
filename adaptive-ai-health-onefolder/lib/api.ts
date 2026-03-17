import type { IntakePayload, PredictResponse } from "@/lib/types";

export type ApiErrorShape = {
  message: string;
  code?: string;
  details?: unknown;
};

async function readJsonSafe(res: Response) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function postIntake(payload: IntakePayload) {
  const res = await fetch("/api/intake", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const body = await readJsonSafe(res);
    throw new Error(
      (body as ApiErrorShape | null)?.message ?? "Failed to submit intake"
    );
  }
  return (await res.json()) as { ok: true; intakeId: string };
}

export async function postPredict(payload: IntakePayload) {
  const res = await fetch("/api/predict", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const body = await readJsonSafe(res);
    throw new Error(
      (body as ApiErrorShape | null)?.message ?? "Failed to fetch predictions"
    );
  }
  return (await res.json()) as PredictResponse;
}

export async function postGenerateReport(payload: {
  intake: IntakePayload;
  predictions: PredictResponse["predictions"];
}) {
  const res = await fetch("/api/report/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const body = await readJsonSafe(res);
    throw new Error(
      (body as ApiErrorShape | null)?.message ?? "Failed to generate report"
    );
  }
  const blob = await res.blob();
  return blob;
}

