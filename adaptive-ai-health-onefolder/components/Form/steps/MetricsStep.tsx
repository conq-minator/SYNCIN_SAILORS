import { Field, Input } from "@/components/Form/Field";
import type { StepProps } from "./types";

export function MetricsStep({ intake, errors, dispatch }: StepProps) {
  const m = intake.bodyMetrics;
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <Field label="Height (cm)" error={errors["bodyMetrics.heightCm"]}>
        <Input
          type="number"
          min={30}
          max={250}
          value={m.heightCm}
          onChange={(e) =>
            dispatch({ type: "setField", path: "bodyMetrics.heightCm", value: e.target.value })
          }
        />
      </Field>
      <Field label="Weight (kg)" error={errors["bodyMetrics.weightKg"]}>
        <Input
          type="number"
          min={2}
          max={350}
          value={m.weightKg}
          onChange={(e) =>
            dispatch({ type: "setField", path: "bodyMetrics.weightKg", value: e.target.value })
          }
        />
      </Field>
    </div>
  );
}

