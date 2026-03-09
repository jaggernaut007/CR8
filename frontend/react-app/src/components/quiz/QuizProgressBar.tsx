/**
 * QuizProgressBar — shows quiz completion progress with question counter.
 */

interface QuizProgressBarProps {
  current: number;
  total: number;
  answered: number;
}

export default function QuizProgressBar({
  current,
  total,
  answered,
}: QuizProgressBarProps) {
  const percent = total > 0 ? (answered / total) * 100 : 0;

  return (
    <div className="glass rounded-lg p-4">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium text-text-primary">
          Question {current} of {total}
        </span>
        <span className="text-text-secondary" data-testid="answered-count">
          {answered} answered
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-bg-tertiary">
        <div
          className="accent-gradient h-full rounded-full transition-all duration-300"
          style={{ width: `${percent}%` }}
          role="progressbar"
          aria-valuenow={answered}
          aria-valuemin={0}
          aria-valuemax={total}
          data-testid="progress-fill"
        />
      </div>
    </div>
  );
}
