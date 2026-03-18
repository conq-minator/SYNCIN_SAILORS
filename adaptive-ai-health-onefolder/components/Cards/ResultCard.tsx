import type { PredictionCard } from "@/lib/types";

const riskStyles: Record<
  PredictionCard["risk"],
  { badge: string; ring: string }
> = {
  low: { badge: "bg-clinic-greenSoft text-clinic-green", ring: "ring-clinic-green/20" },
  moderate: {
    badge: "bg-clinic-amberSoft text-amber-700",
    ring: "ring-amber-200"
  },
  high: { badge: "bg-clinic-redSoft text-red-700", ring: "ring-red-200" }
};

type Props = {
  card: PredictionCard;
  onOpen: () => void;
};

export function ResultCard({ card, onOpen }: Props) {
  // Use a fallback to 'moderate' if the risk style is missing
  const styles = riskStyles[card.risk] || riskStyles.moderate;

  return (
    <button
      onClick={onOpen}
      className={[
        "group w-full rounded-2xl border border-clinic-border bg-white p-5 text-left shadow-card transition",
        "hover:-translate-y-0.5 hover:shadow-[0_16px_42px_rgba(15,23,42,0.10)]",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-clinic-blue focus-visible:ring-offset-2",
        "ring-1",
        styles.ring
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-900">
            {card.diseaseName}
          </div>
          <div className="mt-1 text-xs text-slate-500 line-clamp-2">
            {card.summary}
          </div>
        </div>
        <div className={["shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold", styles.badge].join(" ")}>
          {card.risk.toUpperCase()} RISK
        </div>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-slate-700">Confidence</span>
          <span className="font-semibold text-slate-900">{Math.round(card.confidence)}%</span>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-clinic-blue transition-[width] duration-500"
            style={{ width: `${Math.max(0, Math.min(100, card.confidence))}%` }}
          />
        </div>
        <div className="mt-3 text-xs text-slate-500">
          Click for details
        </div>
      </div>
    </button>
  );
}

