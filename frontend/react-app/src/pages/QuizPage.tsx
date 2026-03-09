/**
 * QuizPage — take a quiz one question at a time.
 *
 * Fetches quiz data, navigates between questions, collects answers,
 * and submits for scoring. Redirects to results if already attempted.
 */

import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchQuiz, submitQuiz } from "@/api/quiz";
import QuestionCard from "@/components/quiz/QuestionCard";
import QuizProgressBar from "@/components/quiz/QuizProgressBar";

export default function QuizPage() {
  const { quizId } = useParams<{ quizId: string }>();
  const navigate = useNavigate();
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});

  const { data: quiz, isLoading, error } = useQuery({
    queryKey: ["quiz", quizId],
    queryFn: () => fetchQuiz(quizId!),
    enabled: !!quizId,
  });

  const mutation = useMutation({
    mutationFn: () => {
      const responses = Object.entries(answers).map(([question_id, selected_index]) => ({
        question_id,
        selected_index,
      }));
      return submitQuiz(quizId!, responses);
    },
    onSuccess: () => navigate(`/quiz/${quizId}/results`),
  });

  const handleSelect = useCallback(
    (index: number) => {
      if (!quiz) return;
      const qId = quiz.questions[current].id;
      setAnswers((prev) => ({ ...prev, [qId]: index }));
    },
    [quiz, current],
  );

  // Redirect if already attempted
  if (quiz?.existing_attempt?.completed_at) {
    navigate(`/quiz/${quizId}/results`, { replace: true });
    return null;
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="glass p-12 text-center text-text-secondary">
          Loading quiz...
        </div>
      </div>
    );
  }

  if (error || !quiz) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="badge-error rounded-lg p-4 text-sm">
          Failed to load quiz.
        </div>
      </div>
    );
  }

  const questions = quiz.questions;
  const totalQuestions = questions.length;
  const question = questions[current];
  const answeredCount = Object.keys(answers).length;
  const allAnswered = answeredCount === totalQuestions;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      {/* Title */}
      <h1 className="mb-4 text-xl font-bold">{quiz.title}</h1>

      {/* Progress */}
      <QuizProgressBar
        current={current + 1}
        total={totalQuestions}
        answered={answeredCount}
      />

      {/* Question */}
      <div className="mt-6">
        <QuestionCard
          question={question}
          questionNumber={current + 1}
          selectedIndex={answers[question.id]}
          onSelect={handleSelect}
          disabled={mutation.isPending}
        />
      </div>

      {/* Navigation */}
      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={() => setCurrent((c) => Math.max(0, c - 1))}
          disabled={current === 0}
          className="glass rounded-lg px-4 py-2 text-sm font-medium transition hover:glass-hover disabled:opacity-40"
        >
          Previous
        </button>

        {current < totalQuestions - 1 ? (
          <button
            onClick={() => setCurrent((c) => Math.min(totalQuestions - 1, c + 1))}
            className="accent-gradient rounded-lg px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
          >
            Next
          </button>
        ) : (
          <button
            onClick={() => mutation.mutate()}
            disabled={!allAnswered || mutation.isPending}
            className="accent-gradient rounded-lg px-6 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
            data-testid="submit-quiz"
          >
            {mutation.isPending ? "Submitting..." : "Submit Quiz"}
          </button>
        )}
      </div>

      {/* Mutation error */}
      {mutation.isError && (
        <div className="mt-4 badge-error rounded-lg p-3 text-sm">
          Failed to submit quiz. Please try again.
        </div>
      )}
    </div>
  );
}
