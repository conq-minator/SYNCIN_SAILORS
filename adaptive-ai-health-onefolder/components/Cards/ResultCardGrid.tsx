import type { PredictionCard } from "@/lib/types";
import { ResultCard } from "./ResultCard";

type Props = {
  cards: PredictionCard[];
  onSelect: (card: PredictionCard) => void;
};

export function ResultCardGrid({ cards, onSelect }: Props) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((c) => (
        <ResultCard key={c.id} card={c} onOpen={() => onSelect(c)} />
      ))}
    </div>
  );
}

