import { Field, Input, Select } from "@/components/Form/Field";
import type { StepProps } from "./types";

export function LifestyleStep({ intake, errors, dispatch }: StepProps) {
  const l = intake.lifestyle;
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <Field label="Sleep (hours/night)" hint="Optional" error={errors["lifestyle.sleepHours"]}>
        <Input
          type="number"
          step="0.5"
          value={l.sleepHours ?? ""}
          placeholder="e.g., 7.5"
          onChange={(e) => dispatch({ type: "setField", path: "lifestyle.sleepHours", value: e.target.value })}
        />
      </Field>

      <Field label="Stress level (1–5)" hint="Optional" error={errors["lifestyle.stressLevel"]}>
        <Select
          value={l.stressLevel ?? ""}
          onChange={(e) =>
            dispatch({ type: "setField", path: "lifestyle.stressLevel", value: e.target.value || undefined })
          }
        >
          <option value="">Not provided</option>
          <option value="1">1 - Low</option>
          <option value="2">2</option>
          <option value="3">3 - Moderate</option>
          <option value="4">4</option>
          <option value="5">5 - High</option>
        </Select>
      </Field>

      <Field label="Activity level" hint="Optional" error={errors["lifestyle.activityLevel"]}>
        <Select
          value={l.activityLevel ?? ""}
          onChange={(e) =>
            dispatch({ type: "setField", path: "lifestyle.activityLevel", value: e.target.value || undefined })
          }
        >
          <option value="">Not provided</option>
          <option value="low">Low</option>
          <option value="moderate">Moderate</option>
          <option value="high">High</option>
        </Select>
      </Field>
    </div>
  );
}

