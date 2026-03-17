type Props = {
  label?: string;
};

export function AnalyzingLoader({ label = "Analyzing your inputs..." }: Props) {
  return (
    <div className="rounded-2xl border border-clinic-border bg-white p-6 shadow-card">
      <div className="flex items-center gap-3">
        <div className="relative h-10 w-10">
          <div className="absolute inset-0 rounded-full border-2 border-clinic-border" />
          <div className="absolute inset-0 animate-spin rounded-full border-2 border-clinic-blue border-t-transparent" />
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-900">{label}</div>
          <div className="text-xs text-slate-500">
            This may take a few seconds.
          </div>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        <SkeletonLine />
        <SkeletonLine />
        <SkeletonLine className="w-2/3" />
      </div>
    </div>
  );
}

function SkeletonLine({ className = "" }: { className?: string }) {
  return (
    <div
      className={[
        "h-3 w-full animate-pulse rounded-full bg-slate-100",
        className
      ].join(" ")}
    />
  );
}

