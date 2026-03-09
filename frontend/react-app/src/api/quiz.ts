/**
 * Quiz API — typed functions for quiz generation, retrieval, submission, and results.
 *
 * All quiz-related types and API calls live here. Pages import from this module
 * instead of defining inline interfaces.
 */

import { apiFetch } from "./client";

// ── Types ──────────────────────────────────────────────────────────────

export interface QuizQuestion {
  id: string;
  question_text: string;
  options: string[];
  difficulty?: string;
  blooms_level?: string;
  correct_index?: number;
  feedback_correct?: string;
  feedback_incorrect?: string;
}

export interface QuizAttempt {
  id: string;
  score: number | null;
  total_questions: number | null;
  completed_at: string | null;
}

export interface Quiz {
  quiz_id: string;
  title: string;
  questions: QuizQuestion[];
  existing_attempt: QuizAttempt | null;
}

export interface SubmitResult {
  attempt_id: string;
  score: number;
  total: number;
  results: QuestionResult[];
}

export interface QuestionResult {
  question_id: string;
  selected_index: number;
  correct_index: number;
  is_correct: boolean;
  feedback: string;
}

export interface QuizResultsResponse {
  score: number;
  total: number;
  percentage: number;
  per_question_results: PerQuestionResult[];
}

export interface PerQuestionResult {
  question_id: string;
  question_text: string;
  options: string[];
  correct_index: number;
  difficulty: string | null;
  blooms_level: string | null;
  feedback_correct: string;
  feedback_incorrect: string;
}

export interface QuizListItem {
  id: string;
  title: string;
  created_at: string;
}

export interface QuizListResponse {
  quizzes: QuizListItem[];
}

// ── API Functions ──────────────────────────────────────────────────────

export function generateQuiz(
  jobId: string,
  questionCount = 20,
): Promise<{ quiz_id: string; question_count: number }> {
  return apiFetch("/api/quiz/generate", {
    method: "POST",
    body: JSON.stringify({ job_id: jobId, question_count: questionCount }),
  });
}

export function fetchQuiz(quizId: string): Promise<Quiz> {
  return apiFetch<Quiz>(`/api/quiz/${quizId}`);
}

export function submitQuiz(
  quizId: string,
  responses: { question_id: string; selected_index: number; time_spent_seconds?: number }[],
): Promise<SubmitResult> {
  return apiFetch<SubmitResult>(`/api/quiz/${quizId}/submit`, {
    method: "POST",
    body: JSON.stringify({ responses }),
  });
}

export function fetchQuizResults(quizId: string): Promise<QuizResultsResponse> {
  return apiFetch<QuizResultsResponse>(`/api/quiz/${quizId}/results`);
}

export function fetchQuizzesByJob(jobId: string): Promise<QuizListResponse> {
  return apiFetch<QuizListResponse>(`/api/quiz/by-job/${jobId}`);
}
