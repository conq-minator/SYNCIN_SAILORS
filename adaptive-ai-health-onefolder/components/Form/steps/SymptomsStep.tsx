import { Field, Input, Select } from "@/components/Form/Field";
import type { StepProps } from "./types";

export function SymptomsStep({ intake, errors, dispatch }: StepProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-900">Symptoms</div>
          <div className="text-xs text-slate-500">
            Add symptoms and quantify duration, intensity, and frequency.
          </div>
        </div>
        <button
          type="button"
          onClick={() => dispatch({ type: "addSymptom" })}
          className="rounded-xl bg-clinic-blue px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:opacity-95"
        >
          Add symptom
        </button>
      </div>

      {errors["symptoms"] ? (
        <div className="rounded-xl border border-red-200 bg-clinic-redSoft px-4 py-3 text-sm font-medium text-red-800">
          {errors["symptoms"]}
        </div>
      ) : null}

      <div className="space-y-4">
        {intake.symptoms.map((s, i) => (
          <div
            key={i}
            className="rounded-2xl border border-clinic-border bg-white p-4 shadow-sm"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs font-semibold text-slate-700">
                Symptom {i + 1}
              </div>
              {intake.symptoms.length > 1 ? (
                <button
                  type="button"
                  onClick={() => dispatch({ type: "removeSymptom", index: i })}
                  className="rounded-lg px-2 py-1 text-xs font-semibold text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
                >
                  Remove
                </button>
              ) : null}
            </div>

            <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field label="Name" error={errors[`symptoms.${i}.name`]}>
                <Input
                  value={s.name}
                  placeholder="e.g., sore throat"
                  onChange={(e) =>
                    dispatch({
                      type: "setField",
                      path: `symptoms.${i}.name`,
                      value: e.target.value
                    })
                  }
                />
              </Field>

              <Field
                label="Duration (days)"
                error={errors[`symptoms.${i}.durationDays`]}
              >
                <Input
                  type="number"
                  min={0}
                  value={s.durationDays}
                  onChange={(e) =>
                    dispatch({
                      type: "setField",
                      path: `symptoms.${i}.durationDays`,
                      value: e.target.value
                    })
                  }
                />
              </Field>

              <Field
                label="Intensity (1–5)"
                error={errors[`symptoms.${i}.intensity`]}
              >
                <Select
                  value={s.intensity}
                  onChange={(e) =>
                    dispatch({
                      type: "setField",
                      path: `symptoms.${i}.intensity`,
                      value: e.target.value
                    })
                  }
                >
                  <option value="1">1 - Mild</option>
                  <option value="2">2</option>
                  <option value="3">3 - Moderate</option>
                  <option value="4">4</option>
                  <option value="5">5 - Severe</option>
                </Select>
              </Field>

              <Field
                label="Frequency (per day)"
                error={errors[`symptoms.${i}.frequencyPerDay`]}
              >
                <Input
                  type="number"
                  min={0}
                  value={s.frequencyPerDay}
                  onChange={(e) =>
                    dispatch({
                      type: "setField",
                      path: `symptoms.${i}.frequencyPerDay`,
                      value: e.target.value
                    })
                  }
                />
              </Field>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

