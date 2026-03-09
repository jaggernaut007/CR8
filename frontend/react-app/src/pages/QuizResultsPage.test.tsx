import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders, setMockAuth, resetMockAuth } from "@/test/test-utils";
import QuizResultsPage from "./QuizResultsPage";

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useParams: () => ({ quizId: "quiz-1" }),
  };
});

vi.mock("@/api/quiz", () => ({
  fetchQuizResults: vi.fn(),
}));

import { fetchQuizResults } from "@/api/quiz";

const mockResults = {
  score: 80,
  total: 10,
  percentage: 80,
  per_question_results: [
    {
      question_id: "q1",
      question_text: "What is 2+2?",
      options: ["3", "4", "5", "6"],
      correct_index: 1,
      difficulty: "easy",
      blooms_level: "remember",
      feedback_correct: "Right!",
      feedback_incorrect: "Wrong, it's 4",
    },
  ],
};

describe("QuizResultsPage", () => {
  beforeEach(() => {
    resetMockAuth();
    setMockAuth({ user: { id: "u1", email: "test@test.com", display_name: null, role: "user" } });
    vi.mocked(fetchQuizResults).mockResolvedValue(mockResults);
  });

  it("shows loading state", () => {
    vi.mocked(fetchQuizResults).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<QuizResultsPage />);
    expect(screen.getByText("Loading results...")).toBeInTheDocument();
  });

  it("renders score summary", async () => {
    renderWithProviders(<QuizResultsPage />);
    await waitFor(() => {
      expect(screen.getByTestId("score-summary")).toBeInTheDocument();
    });
    expect(screen.getByText("80%")).toBeInTheDocument();
  });

  it("renders per-question results", async () => {
    renderWithProviders(<QuizResultsPage />);
    await waitFor(() => {
      expect(screen.getByText("What is 2+2?")).toBeInTheDocument();
    });
  });

  it("shows back to dashboard link", async () => {
    renderWithProviders(<QuizResultsPage />);
    await waitFor(() => {
      expect(screen.getByText("Back to Dashboard")).toBeInTheDocument();
    });
  });

  it("shows error on fetch failure", async () => {
    vi.mocked(fetchQuizResults).mockRejectedValue(new Error("fail"));
    renderWithProviders(<QuizResultsPage />);
    await waitFor(() => {
      expect(screen.getByText("Failed to load quiz results.")).toBeInTheDocument();
    });
  });
});
