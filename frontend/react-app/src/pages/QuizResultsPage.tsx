/**
 * QuizResultsPage — shows scored quiz results with per-question feedback.
 *
 * Displays score summary at top, followed by all questions in review mode
 * showing correct/incorrect answers and feedback text.
 */

import { useParams, Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { fetchQuizResults } from "@/api/quiz";
import ScoreSummary from "@/components/quiz/ScoreSummary";
import QuestionCard from "@/components/quiz/QuestionCard";

export default function QuizResultsPage() {
  const { quizId } = useParams<{ quizId: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["quizResults", quizId],
    queryFn: () => fetchQuizResults(quizId!),
    enabled: !!quizId,
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="glass p-12 text-center text-text-secondary">
          Loading results...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="badge-error rounded-lg p-4 text-sm">
          Failed to load quiz results.
        </div>
      </div>
    );
  }

  const correctCount = Math.round((data.percentage / 100) * data.total);

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-6 text-xl font-bold">Quiz Results</h1>

      {/* Score summary */}
      <ScoreSummary
        score={correctCount}
        total={data.total}
        percentage={data.percentage}
      />

      {/* Per-question results */}
      <div className="mt-8 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
          Question Review
        </h2>
        {data.per_question_results.map((q, idx) => (
          <QuestionCard
            key={q.question_id}
            question={{
              id: q.question_id,
              question_text: q.question_text,
              options: q.options,
              difficulty: q.difficulty ?? undefined,
            }}
            questionNumber={idx + 1}
            selectedIndex={undefined}
            onSelect={() => {}}
            showResult
            correctIndex={q.correct_index}
            feedback={q.feedback_correct || q.feedback_incorrect}
            disabled
          />
        ))}
      </div>

      {/* Back link */}
      <Link
        to="/dashboard"
        className="mt-6 inline-block accent-gradient rounded-lg px-6 py-2.5 font-medium text-white transition hover:opacity-90"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
