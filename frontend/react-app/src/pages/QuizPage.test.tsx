import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders, setMockAuth, resetMockAuth } from "@/test/test-utils";
import QuizPage from "./QuizPage";

// Mock react-router hooks
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useParams: () => ({ quizId: "quiz-1" }),
    useNavigate: () => mockNavigate,
  };
});

// Mock quiz API
vi.mock("@/api/quiz", () => ({
  fetchQuiz: vi.fn(),
  submitQuiz: vi.fn(),
}));

import { fetchQuiz } from "@/api/quiz";

const mockQuiz = {
  quiz_id: "quiz-1",
  title: "Test Quiz",
  questions: [
    { id: "q1", question_text: "Q1?", options: ["A", "B", "C", "D"], difficulty: "easy" },
    { id: "q2", question_text: "Q2?", options: ["X", "Y", "Z", "W"], difficulty: "medium" },
  ],
  existing_attempt: null,
};

describe("QuizPage", () => {
  beforeEach(() => {
    resetMockAuth();
    setMockAuth({ user: { id: "u1", email: "test@test.com", display_name: null, role: "user" } });
    vi.mocked(fetchQuiz).mockResolvedValue(mockQuiz);
    mockNavigate.mockClear();
  });

  it("shows loading state initially", () => {
    vi.mocked(fetchQuiz).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<QuizPage />);
    expect(screen.getByText("Loading quiz...")).toBeInTheDocument();
  });

  it("renders quiz title and first question", async () => {
    renderWithProviders(<QuizPage />);
    await waitFor(() => {
      expect(screen.getByText("Test Quiz")).toBeInTheDocument();
    });
    expect(screen.getByText("Q1?")).toBeInTheDocument();
  });

  it("navigates between questions with prev/next", async () => {
    renderWithProviders(<QuizPage />);
    await waitFor(() => expect(screen.getByText("Q1?")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByText("Q2?")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Previous"));
    expect(screen.getByText("Q1?")).toBeInTheDocument();
  });

  it("shows submit button on last question", async () => {
    renderWithProviders(<QuizPage />);
    await waitFor(() => expect(screen.getByText("Q1?")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByTestId("submit-quiz")).toBeInTheDocument();
  });

  it("disables submit until all questions answered", async () => {
    renderWithProviders(<QuizPage />);
    await waitFor(() => expect(screen.getByText("Q1?")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByTestId("submit-quiz")).toBeDisabled();
  });

  it("shows error state on fetch failure", async () => {
    vi.mocked(fetchQuiz).mockRejectedValue(new Error("fail"));
    renderWithProviders(<QuizPage />);
    await waitFor(() => {
      expect(screen.getByText("Failed to load quiz.")).toBeInTheDocument();
    });
  });

  // ── Redirect on completed attempt (reviewer gap) ─────────────────────────

  it("redirects to results when existing_attempt has completed_at", async () => {
    // Quiz data where the user already completed this quiz
    vi.mocked(fetchQuiz).mockResolvedValue({
      ...mockQuiz,
      existing_attempt: {
        id: "attempt-99",
        score: 80,
        total_questions: 2,
        completed_at: "2026-03-09T10:00:00Z",
      },
    });

    renderWithProviders(<QuizPage />);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        "/quiz/quiz-1/results",
        expect.objectContaining({ replace: true }),
      );
    });
  });

  it("does not redirect when existing_attempt is null", async () => {
    // Standard quiz with no previous attempt
    vi.mocked(fetchQuiz).mockResolvedValue({ ...mockQuiz, existing_attempt: null });

    renderWithProviders(<QuizPage />);

    await waitFor(() => {
      expect(screen.getByText("Q1?")).toBeInTheDocument();
    });

    expect(mockNavigate).not.toHaveBeenCalledWith(
      expect.stringContaining("results"),
      expect.anything(),
    );
  });

  it("does not redirect when existing_attempt has no completed_at", async () => {
    // Attempt exists but not completed (e.g., abandoned mid-quiz)
    vi.mocked(fetchQuiz).mockResolvedValue({
      ...mockQuiz,
      existing_attempt: {
        id: "attempt-50",
        score: null,
        total_questions: null,
        completed_at: null,
      },
    });

    renderWithProviders(<QuizPage />);

    await waitFor(() => {
      expect(screen.getByText("Q1?")).toBeInTheDocument();
    });

    expect(mockNavigate).not.toHaveBeenCalledWith(
      expect.stringContaining("results"),
      expect.anything(),
    );
  });
});
