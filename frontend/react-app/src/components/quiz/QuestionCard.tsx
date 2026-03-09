/**
 * QuestionCard — renders a single MCQ question with selectable options.
 *
 * Supports two modes: answer mode (selecting options) and review mode
 * (showing correct/wrong with feedback after submission).
 */

interface QuestionCardProps {
  question: {
    id: string;
    question_text: string;
    options: string[];
    difficulty?: string;
  };
  questionNumber: number;
  selectedIndex: number | undefined;
  onSelect: (index: number) => void;
  showResult?: boolean;
  correctIndex?: number;
  feedback?: string;
  disabled?: boolean;
}

const DIFFICULTY_STYLES: Record<string, string> = {
  easy: "badge-success",
  medium: "badge-warning",
  hard: "badge-error",
};

export default function QuestionCard({
  question,
  questionNumber,
  selectedIndex,
  onSelect,
  showResult = false,
  correctIndex,
  feedback,
  disabled = false,
}: QuestionCardProps) {
  return (
    <div className="glass glass-shadow p-6" data-testid="question-card">
      {/* Header: question number + difficulty badge */}
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm font-semibold text-text-secondary">
          Question {questionNumber}
        </span>
        {question.difficulty && (
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${DIFFICULTY_STYLES[question.difficulty] ?? "badge-warning"}`}
            data-testid="difficulty-badge"
          >
            {question.difficulty}
          </span>
        )}
      </div>

      {/* Question text */}
      <p className="mb-5 text-lg font-medium text-text-primary">
        {question.question_text}
      </p>

      {/* Options */}
      <div className="space-y-2">
        {question.options.map((option, idx) => (
          <button
            key={idx}
            onClick={() => !disabled && onSelect(idx)}
            disabled={disabled}
            className={`w-full rounded-lg border p-3 text-left text-sm transition ${optionStyle(idx, selectedIndex, showResult, correctIndex)}`}
            data-testid={`option-${idx}`}
            aria-pressed={selectedIndex === idx}
          >
            <span className="mr-2 font-semibold text-text-muted">
              {String.fromCharCode(65 + idx)}.
            </span>
            {option}
          </button>
        ))}
      </div>

      {/* Feedback (review mode only) */}
      {showResult && feedback && (
        <div
          className={`mt-4 rounded-lg p-3 text-sm ${selectedIndex === correctIndex ? "badge-success" : "badge-error"}`}
          data-testid="feedback"
        >
          {feedback}
        </div>
      )}
    </div>
  );
}

function optionStyle(
  idx: number,
  selectedIndex: number | undefined,
  showResult: boolean,
  correctIndex: number | undefined,
): string {
  if (showResult && correctIndex !== undefined) {
    if (idx === correctIndex) {
      return "border-success bg-success/10 text-text-primary";
    }
    if (idx === selectedIndex && idx !== correctIndex) {
      return "border-error bg-error/10 text-text-primary";
    }
    return "border-border-glass bg-transparent text-text-muted";
  }

  if (idx === selectedIndex) {
    return "border-accent-blue bg-accent-blue/10 text-text-primary";
  }
  return "border-border-glass bg-transparent text-text-secondary hover:border-accent-blue/50 hover:bg-bg-glass-hover";
}
