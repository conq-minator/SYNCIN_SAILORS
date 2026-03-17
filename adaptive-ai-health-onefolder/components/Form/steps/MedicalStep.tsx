import { Field, Textarea } from "@/components/Form/Field";
import type { StepProps } from "./types";

export function MedicalStep({ intake, errors, dispatch }: StepProps) {
  const mi = intake.medicalInfo;
  return (
    <div className="grid grid-cols-1 gap-4">
      <Field label="Known conditions" hint="Optional" error={errors["medicalInfo.conditions"]}>
        <Textarea
          value={mi.conditions}
          placeholder="e.g., asthma, thyroid condition, diabetes..."
          onChange={(e) =>
            dispatch({ type: "setField", path: "medicalInfo.conditions", value: e.target.value })
          }
        />
      </Field>
      <Field label="Allergies" hint="Optional" error={errors["medicalInfo.allergies"]}>
        <Textarea
          value={mi.allergies}
          placeholder="e.g., penicillin, peanuts..."
          onChange={(e) =>
            dispatch({ type: "setField", path: "medicalInfo.allergies", value: e.target.value })
          }
        />
      </Field>
      <Field label="Current medications" hint="Optional" error={errors["medicalInfo.medications"]}>
        <Textarea
          value={mi.medications}
          placeholder="e.g., metformin 500mg..."
          onChange={(e) =>
            dispatch({ type: "setField", path: "medicalInfo.medications", value: e.target.value })
          }
        />
      </Field>
    </div>
  );
}

