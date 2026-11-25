import { ArrowDownRight, Check, Minus } from 'lucide-react';

interface RelevanceBadgeProps {
  score: number | null | undefined;
}

export function RelevanceBadge({ score }: RelevanceBadgeProps) {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return (
      <span className="badge badge-neutral">
        <Minus size={12} aria-hidden="true" />
        <span>Relevance pending</span>
      </span>
    );
  }

  const pct = Math.round(score * 100);
  if (score >= 0.75) {
    return (
      <span className="badge badge-success">
        <Check size={12} aria-hidden="true" />
        <span>High match · {pct}%</span>
      </span>
    );
  }

  if (score >= 0.5) {
    return (
      <span className="badge badge-warning">
        <Minus size={12} aria-hidden="true" />
        <span>Medium match · {pct}%</span>
      </span>
    );
  }

  return (
    <span className="badge badge-neutral">
      <ArrowDownRight size={12} aria-hidden="true" />
      <span>Low match · {pct}%</span>
    </span>
  );
}
