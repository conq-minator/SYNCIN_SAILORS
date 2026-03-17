import type { IntakePayload, PredictResponse } from "@/lib/types";

const KEY = "adaptive-ai-health:latest";

export function saveSession(data: {
  intake: IntakePayload;
  result: PredictResponse;
}) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(KEY, JSON.stringify(data));
}

export function loadSession():
  | { intake: IntakePayload; result: PredictResponse }
  | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(KEY);
}

