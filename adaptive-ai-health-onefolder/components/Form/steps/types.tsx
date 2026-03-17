import type { IntakePayload } from "@/lib/types";
import type { IntakeAction } from "@/components/Form/intakeReducer";
import type React from "react";

export type StepProps = {
  intake: IntakePayload;
  errors: Record<string, string>;
  dispatch: React.Dispatch<IntakeAction>;
};

