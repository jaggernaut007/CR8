import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders, resetMockAuth } from "@/test/test-utils";
import ResultsPage from "./ResultsPage";

vi.mock("@/api/jobs", () => ({
  fetchJob: vi.fn(),
  startPipeline: vi.fn(),
  downloadUrl: vi.fn((jobId: string, type: string) => `/api/download/${jobId}/${type}`),
  fetchSlides: vi.fn().mockResolvedValue({ slides: [], total: 0 }),
  fetchVideos: vi.fn().mockResolvedValue({ videos: [] }),
  viewPdfUrl: vi.fn((jobId: string) => `/api/view/${jobId}/pdf`),
  viewSlideUrl: vi.fn((jobId: string, i: number) => `/api/view/${jobId}/slide/${i}`),
  viewVideoUrl: vi.fn((jobId: string, i: number) => `/api/view/${jobId}/video/${i}`),
}));

// Mock quiz API — default to empty quiz list and a no-op generate
vi.mock("@/api/quiz", () => ({
  fetchQuizzesByJob: vi.fn(),
  generateQuiz: vi.fn(),
}));

import { fetchJob, startPipeline } from "@/api/jobs";
import { fetchQuizzesByJob, generateQuiz } from "@/api/quiz";
const mockFetchJob = vi.mocked(fetchJob);
const mockStartPipeline = vi.mocked(startPipeline);
const mockFetchQuizzesByJob = vi.mocked(fetchQuizzesByJob);
const mockGenerateQuiz = vi.mocked(generateQuiz);

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useParams: () => ({ jobId: "job-456" }),
    useNavigate: () => mockNavigate,
  };
});

const _completeJob = {
  id: "job-456",
  filename: "lecture.pdf",
  status: "complete" as const,
  stage: null,
  percent: 100,
  created_at: "2026-03-01T00:00:00Z",
  formats: ["pdf", "ppt", "video"],
};

const _completeJobNoVideo = {
  id: "job-456",
  filename: "lecture.pdf",
  status: "complete" as const,
  stage: null,
  percent: 100,
  created_at: "2026-03-01T00:00:00Z",
  formats: ["pdf", "ppt"],
};

beforeEach(() => {
  resetMockAuth();
  vi.clearAllMocks();
  mockFetchQuizzesByJob.mockResolvedValue({ quizzes: [] });
  mockGenerateQuiz.mockResolvedValue({ quiz_id: "new-quiz-1", question_count: 20 });
  mockStartPipeline.mockResolvedValue({ status: "running" });
  mockNavigate.mockClear();
});

describe("ResultsPage", () => {
  it("shows loading state", () => {
    mockFetchJob.mockReturnValue(new Promise(() => {}));
    renderWithProviders(<ResultsPage />);
    expect(screen.getByText("Loading results...")).toBeInTheDocument();
  });

  it("shows error state with recovery link", async () => {
    mockFetchJob.mockRejectedValue(new Error("Not found"));
    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load job details.")).toBeInTheDocument();
      expect(screen.getByText("Back to Dashboard")).toBeInTheDocument();
    });
  });

  it("renders complete job with download buttons", async () => {
    mockFetchJob.mockResolvedValue(_completeJob);

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Generation Complete")).toBeInTheDocument();
      expect(screen.getByText("lecture.pdf")).toBeInTheDocument();
    });

    // Should show the 3 download types for pdf+ppt+video
    // (script downloads were intentionally removed in d685634)
    expect(screen.getByText("Learning Guide")).toBeInTheDocument();
    expect(screen.getByText("Slide Deck")).toBeInTheDocument();
    expect(screen.getByText("Videos")).toBeInTheDocument();
    expect(screen.queryByText("Video Scripts")).not.toBeInTheDocument();
  });

  it("shows only PDF download for pdf-only job", async () => {
    mockFetchJob.mockResolvedValue({
      id: "job-456",
      filename: "notes.pdf",
      status: "complete",
      stage: null,
      percent: 100,
      created_at: "2026-03-01T00:00:00Z",
      formats: ["pdf"],
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Learning Guide")).toBeInTheDocument();
    });

    expect(screen.queryByText("Slide Deck")).not.toBeInTheDocument();
    expect(screen.queryByText("Videos")).not.toBeInTheDocument();
  });

  it("hides download buttons for non-complete jobs", async () => {
    mockFetchJob.mockResolvedValue({
      id: "job-456",
      filename: "lecture.pdf",
      status: "error",
      stage: "Generate",
      percent: 50,
      created_at: "2026-03-01T00:00:00Z",
      formats: ["pdf", "ppt"],
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Job error")).toBeInTheDocument();
    });

    expect(screen.queryByText("Downloads")).not.toBeInTheDocument();
  });

  it("triggers download on button click", async () => {
    mockFetchJob.mockResolvedValue({
      id: "job-456",
      filename: "lecture.pdf",
      status: "complete",
      stage: null,
      percent: 100,
      created_at: "2026-03-01T00:00:00Z",
      formats: ["pdf"],
    });

    // Mock anchor click
    const clickSpy = vi.fn();
    const createElementOrig = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = createElementOrig(tag);
      if (tag === "a") {
        el.click = clickSpy;
      }
      return el;
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Learning Guide")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Learning Guide").closest("button")!);
    expect(clickSpy).toHaveBeenCalled();

    vi.restoreAllMocks();
  });

  it("shows format labels in metadata", async () => {
    mockFetchJob.mockResolvedValue(_completeJob);

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText(/PDF, Slides, Video/)).toBeInTheDocument();
    });
  });

  it("shows content tabs for complete job", async () => {
    mockFetchJob.mockResolvedValue(_completeJob);

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("content-tabs")).toBeInTheDocument();
    });

    expect(screen.getByText("PDF Guide")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Slides" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Video" })).toBeInTheDocument();
  });

  it("renders PDF viewer by default", async () => {
    mockFetchJob.mockResolvedValue({
      id: "job-456",
      filename: "lecture.pdf",
      status: "complete",
      stage: null,
      percent: 100,
      created_at: "2026-03-01T00:00:00Z",
      formats: ["pdf"],
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pdf-viewer")).toBeInTheDocument();
    });
  });

  it("hides content tabs for non-complete jobs", async () => {
    mockFetchJob.mockResolvedValue({
      id: "job-456",
      filename: "lecture.pdf",
      status: "running",
      stage: "Research",
      percent: 40,
      created_at: "2026-03-01T00:00:00Z",
      formats: ["pdf", "ppt"],
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Job running")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("content-tabs")).not.toBeInTheDocument();
  });
});

// ── QuizSection tests ────────────────────────────────────────────────────────

describe("ResultsPage — QuizSection", () => {
  beforeEach(() => {
    mockFetchJob.mockResolvedValue(_completeJob);
  });

  it("renders quiz-section container for complete job", async () => {
    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("quiz-section")).toBeInTheDocument();
    });
  });

  it("shows generate quiz button when no quizzes exist", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({ quizzes: [] });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-quiz-btn")).toBeInTheDocument();
    });

    expect(screen.getByTestId("generate-quiz-btn")).toHaveTextContent("Generate Quiz");
  });

  it("generate quiz button is enabled by default", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({ quizzes: [] });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-quiz-btn")).toBeInTheDocument();
    });

    expect(screen.getByTestId("generate-quiz-btn")).not.toBeDisabled();
  });

  it("clicking generate quiz calls generateQuiz API", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({ quizzes: [] });
    // Pending promise so navigation doesn't interfere with the click assertion
    mockGenerateQuiz.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-quiz-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-quiz-btn"));

    await waitFor(() => {
      expect(mockGenerateQuiz).toHaveBeenCalledWith("job-456");
    });
  });

  it("shows 'Generating Quiz...' while mutation is pending", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({ quizzes: [] });
    // Never resolves — keeps mutation in isPending state
    mockGenerateQuiz.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-quiz-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-quiz-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("generate-quiz-btn")).toHaveTextContent("Generating Quiz...");
    });
  });

  it("disables generate button while mutation is pending", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({ quizzes: [] });
    mockGenerateQuiz.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-quiz-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-quiz-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("generate-quiz-btn")).toBeDisabled();
    });
  });

  it("navigates to quiz page on successful generation", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({ quizzes: [] });
    mockGenerateQuiz.mockResolvedValue({ quiz_id: "new-quiz-99", question_count: 20 });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-quiz-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-quiz-btn"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/quiz/new-quiz-99");
    });
  });

  it("shows error message when quiz generation fails", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({ quizzes: [] });
    mockGenerateQuiz.mockRejectedValue(new Error("Server error"));

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-quiz-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-quiz-btn"));

    await waitFor(() => {
      expect(screen.getByText("Failed to generate quiz.")).toBeInTheDocument();
    });
  });

  it("renders quiz links when quizzes exist", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({
      quizzes: [
        { id: "q1", title: "Week 1 Quiz", created_at: "2026-03-01T00:00:00Z" },
        { id: "q2", title: "Week 2 Quiz", created_at: "2026-03-05T00:00:00Z" },
      ],
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId("quiz-link")).toHaveLength(2);
    });

    expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    expect(screen.getByText("Week 2 Quiz")).toBeInTheDocument();
  });

  it("hides generate button when quizzes already exist", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({
      quizzes: [{ id: "q1", title: "Existing Quiz", created_at: "2026-03-01T00:00:00Z" }],
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Existing Quiz")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("generate-quiz-btn")).not.toBeInTheDocument();
  });

  it("quiz links point to the correct quiz route", async () => {
    mockFetchQuizzesByJob.mockResolvedValue({
      quizzes: [{ id: "quiz-abc", title: "My Quiz", created_at: "2026-03-01T00:00:00Z" }],
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("quiz-link")).toBeInTheDocument();
    });

    const link = screen.getByTestId("quiz-link");
    expect(link).toHaveAttribute("href", "/quiz/quiz-abc");
  });

  it("does not render quiz-section for non-complete jobs", async () => {
    mockFetchJob.mockResolvedValue({
      ..._completeJob,
      status: "running",
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Job running")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("quiz-section")).not.toBeInTheDocument();
  });
});

// ── AddVideoSection tests ─────────────────────────────────────────────────────

describe("ResultsPage — AddVideoSection", () => {
  it("renders 'Generate Video' button when formats does not include video", async () => {
    mockFetchJob.mockResolvedValue(_completeJobNoVideo);

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-video-btn")).toBeInTheDocument();
    });

    expect(screen.getByTestId("generate-video-btn")).toHaveTextContent("Generate Video");
  });

  it("does not render AddVideoSection when formats already includes video", async () => {
    mockFetchJob.mockResolvedValue(_completeJob); // has video

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Generation Complete")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("generate-video-btn")).not.toBeInTheDocument();
  });

  it("clicking Generate Video calls startPipeline with video added to formats", async () => {
    mockFetchJob.mockResolvedValue(_completeJobNoVideo);
    // Keep pending so we can assert before navigation fires
    mockStartPipeline.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-video-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-video-btn"));

    await waitFor(() => {
      expect(mockStartPipeline).toHaveBeenCalledWith(
        "job-456",
        expect.arrayContaining(["ppt", "video"]),
      );
    });
  });

  it("shows 'Starting Video Generation...' while mutation is pending", async () => {
    mockFetchJob.mockResolvedValue(_completeJobNoVideo);
    mockStartPipeline.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-video-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-video-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("generate-video-btn")).toHaveTextContent(
        "Starting Video Generation...",
      );
    });
  });

  it("button is disabled while mutation is pending", async () => {
    mockFetchJob.mockResolvedValue(_completeJobNoVideo);
    mockStartPipeline.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-video-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-video-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("generate-video-btn")).toBeDisabled();
    });
  });

  it("navigates to /progress/:jobId on successful video generation start", async () => {
    mockFetchJob.mockResolvedValue(_completeJobNoVideo);
    mockStartPipeline.mockResolvedValue({ status: "running" });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-video-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-video-btn"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/progress/job-456");
    });
  });

  it("shows error message when startPipeline fails", async () => {
    mockFetchJob.mockResolvedValue(_completeJobNoVideo);
    mockStartPipeline.mockRejectedValue(new Error("Server error"));

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-video-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-video-btn"));

    await waitFor(() => {
      expect(screen.getByText("Failed to start video generation.")).toBeInTheDocument();
    });
  });
});
