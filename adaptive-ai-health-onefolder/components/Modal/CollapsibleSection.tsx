import { ReactNode, useId, useState } from "react";

type Props = {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
};

export function CollapsibleSection({
  title,
  defaultOpen = true,
  children
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();

  return (
    <section className="rounded-xl border border-clinic-border bg-white">
      <button
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-slate-50"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={id}
      >
        <span className="text-sm font-semibold text-slate-900">{title}</span>
        <span className="text-xs text-slate-500">{open ? "Hide" : "Show"}</span>
      </button>
      {open ? <div id={id} className="px-4 pb-4">{children}</div> : null}
    </section>
  );
}

