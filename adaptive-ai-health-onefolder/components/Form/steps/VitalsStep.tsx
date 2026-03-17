import { Field, Input } from "@/components/Form/Field";
import type { StepProps } from "./types";

export function VitalsStep({ intake, errors, dispatch }: StepProps) {
  const v = intake.vitals;
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <Field label="Blood pressure (systolic)" hint="mmHg" error={errors["vitals.bpSystolic"]}>
        <Input
          type="number"
          value={v.bpSystolic ?? ""}
          placeholder="e.g., 120"
          onChange={(e) => dispatch({ type: "setField", path: "vitals.bpSystolic", value: e.target.value })}
        />
      </Field>
      <Field label="Blood pressure (diastolic)" hint="mmHg" error={errors["vitals.bpDiastolic"]}>
        <Input
          type="number"
          value={v.bpDiastolic ?? ""}
          placeholder="e.g., 80"
          onChange={(e) => dispatch({ type: "setField", path: "vitals.bpDiastolic", value: e.target.value })}
        />
      </Field>
      <Field label="Blood sugar" hint="mg/dL" error={errors["vitals.bloodSugarMgDl"]}>
        <Input
          type="number"
          value={v.bloodSugarMgDl ?? ""}
          placeholder="e.g., 95"
          onChange={(e) => dispatch({ type: "setField", path: "vitals.bloodSugarMgDl", value: e.target.value })}
        />
      </Field>
      <Field label="Heart rate" hint="bpm" error={errors["vitals.heartRateBpm"]}>
        <Input
          type="number"
          value={v.heartRateBpm ?? ""}
          placeholder="e.g., 72"
          onChange={(e) => dispatch({ type: "setField", path: "vitals.heartRateBpm", value: e.target.value })}
        />
      </Field>
      <Field label="Temperature" hint="°C" error={errors["vitals.temperatureC"]}>
        <Input
          type="number"
          step="0.1"
          value={v.temperatureC ?? ""}
          placeholder="e.g., 36.8"
          onChange={(e) => dispatch({ type: "setField", path: "vitals.temperatureC", value: e.target.value })}
        />
      </Field>
    </div>
  );
}

