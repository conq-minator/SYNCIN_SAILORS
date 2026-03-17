import { Field, Textarea } from "@/components/Form/Field";
import type { StepProps } from "./types";

export function AssumptionStep({ intake, errors, dispatch }: StepProps) {
  return (
    <div className="space-y-4">
      <div>
        <div className="text-sm font-semibold text-slate-900">
          Optional assumption
        </div>
        <div className="text-xs text-slate-500">
          If you have a suspicion, share it. This does not affect medical advice.
        </div>
      </div>

      <Field
        label="What do you think you have?"
        hint="Optional"
        error={errors["assumption"]}
      >
        <Textarea
          value={intake.assumption ?? ""}
          placeholder="e.g., seasonal flu"
          onChange={(e) =>
            dispatch({ type: "setField", path: "assumption", value: e.target.value })
          }
        />
      </Field>
    </div>
  );
}

