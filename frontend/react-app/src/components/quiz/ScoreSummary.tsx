/**
 * ScoreSummary — displays quiz score with percentage and color-coded indicator.
 */

interface ScoreSummaryProps {
  score: number;
  total: number;
  percentage: number;
}

export default function ScoreSummary({
  score,
  total,
  percentage,
}: ScoreSummaryProps) {
  const colorClass = scoreColor(percentage);
  const rounded = Math.round(percentage);

  return (
    <div className="glass glass-shadow p-8 text-center" data-testid="score-summary">
      {/* Percentage circle */}
      <div
        className={`mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full border-4 ${colorClass}`}
        data-testid="score-circle"
      >
        <span className="text-3xl font-bold">{rounded}%</span>
      </div>

      {/* Score fraction */}
      <p className="text-lg text-text-secondary" data-testid="score-fraction">
        {score} / {total} correct
      </p>

      {/* Label */}
      <p className={`mt-1 text-sm font-medium ${colorClass.split(" ")[0]}`} data-testid="score-label">
        {scoreLabel(percentage)}
      </p>
    </div>
  );
}

function scoreColor(percentage: number): string {
  if (percentage >= 80) return "text-success border-success";
  if (percentage >= 60) return "text-warning border-warning";
  return "text-error border-error";
}

function scoreLabel(percentage: number): string {
  if (percentage >= 80) return "Excellent";
  if (percentage >= 60) return "Good";
  return "Needs improvement";
}
