import { Field, Input, Select } from "@/components/Form/Field";
import type { StepProps } from "./types";

export function PersonalStep({ intake, errors, dispatch }: StepProps) {
  const p = intake.personalInfo;
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <Field label="Full name" error={errors["personalInfo.fullName"]}>
        <Input
          value={p.fullName}
          placeholder="e.g., Alex Johnson"
          onChange={(e) =>
            dispatch({
              type: "setField",
              path: "personalInfo.fullName",
              value: e.target.value
            })
          }
        />
      </Field>

      <Field label="Date of birth" hint="YYYY-MM-DD" error={errors["personalInfo.dob"]}>
        <Input
          value={p.dob}
          placeholder="1990-08-24"
          onChange={(e) =>
            dispatch({ type: "setField", path: "personalInfo.dob", value: e.target.value })
          }
        />
      </Field>

      <Field label="Gender" error={errors["personalInfo.gender"]}>
        <Select
          value={p.gender}
          onChange={(e) =>
            dispatch({ type: "setField", path: "personalInfo.gender", value: e.target.value })
          }
        >
          <option value="prefer_not_to_say">Prefer not to say</option>
          <option value="female">Female</option>
          <option value="male">Male</option>
          <option value="other">Other</option>
        </Select>
      </Field>

      <Field label="Blood group" error={errors["personalInfo.bloodGroup"]}>
        <Input
          value={p.bloodGroup}
          placeholder="e.g., O+, A-, B+"
          onChange={(e) =>
            dispatch({
              type: "setField",
              path: "personalInfo.bloodGroup",
              value: e.target.value
            })
          }
        />
      </Field>
    </div>
  );
}

