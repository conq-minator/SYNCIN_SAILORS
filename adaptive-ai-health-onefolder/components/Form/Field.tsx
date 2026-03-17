import { ReactNode } from "react";

type Props = {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
};

export function Field({ label, hint, error, children }: Props) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-xs font-semibold text-slate-700">{label}</span>
        {hint ? <span className="text-[11px] text-slate-500">{hint}</span> : null}
      </div>
      <div className="mt-1">{children}</div>
      {error ? (
        <div className="mt-1 text-[11px] font-medium text-red-700">{error}</div>
      ) : null}
    </label>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const { className = "", ...rest } = props;
  return (
    <input
      {...rest}
      className={[
        "w-full rounded-xl border border-clinic-border bg-white px-3 py-2 text-sm text-slate-900",
        "outline-none transition focus:border-clinic-blue focus:ring-2 focus:ring-clinic-blue/20",
        className
      ].join(" ")}
    />
  );
}

export function Textarea(
  props: React.TextareaHTMLAttributes<HTMLTextAreaElement>
) {
  const { className = "", ...rest } = props;
  return (
    <textarea
      {...rest}
      className={[
        "min-h-[84px] w-full resize-y rounded-xl border border-clinic-border bg-white px-3 py-2 text-sm text-slate-900",
        "outline-none transition focus:border-clinic-blue focus:ring-2 focus:ring-clinic-blue/20",
        className
      ].join(" ")}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  const { className = "", ...rest } = props;
  return (
    <select
      {...rest}
      className={[
        "w-full rounded-xl border border-clinic-border bg-white px-3 py-2 text-sm text-slate-900",
        "outline-none transition focus:border-clinic-blue focus:ring-2 focus:ring-clinic-blue/20",
        className
      ].join(" ")}
    />
  );
}

