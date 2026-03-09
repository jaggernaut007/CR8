import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders, resetMockAuth } from "@/test/test-utils";
import ResultsPage from "./ResultsPage";

vi.mock("@/api/jobs", () => ({
  fetchJob: vi.fn(),
  downloadUrl: vi.fn((jobId: string, type: string) => `/api/download/${jobId}/${type}`),
  fetchSlides: vi.fn().mockResolvedValue({ slides: [], total: 0 }),
  fetchVideos: vi.fn().mockResolvedValue({ videos: [] }),
  viewPdfUrl: vi.fn((jobId: string) => `/api/view/${jobId}/pdf`),
  viewSlideUrl: vi.fn((jobId: string, i: number) => `/api/view/${jobId}/slide/${i}`),
  viewVideoUrl: vi.fn((jobId: string, i: number) => `/api/view/${jobId}/video/${i}`),
}));

import { fetchJob } from "@/api/jobs";
const mockFetchJob = vi.mocked(fetchJob);

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useParams: () => ({ jobId: "job-456" }),
  };
});

beforeEach(() => {
  resetMockAuth();
  vi.clearAllMocks();
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
    mockFetchJob.mockResolvedValue({
      id: "job-456",
      filename: "lecture.pdf",
      status: "complete",
      stage: null,
      percent: 100,
      created_at: "2026-03-01T00:00:00Z",
      formats: ["pdf", "ppt", "video"],
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Generation Complete")).toBeInTheDocument();
      expect(screen.getByText("lecture.pdf")).toBeInTheDocument();
    });

    // Should show all 4 download types for pdf+ppt+video
    expect(screen.getByText("Learning Guide")).toBeInTheDocument();
    expect(screen.getByText("Slide Deck")).toBeInTheDocument();
    expect(screen.getByText("Video Scripts")).toBeInTheDocument();
    expect(screen.getByText("Videos")).toBeInTheDocument();
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
    mockFetchJob.mockResolvedValue({
      id: "job-456",
      filename: "lecture.pdf",
      status: "complete",
      stage: null,
      percent: 100,
      created_at: "2026-03-01T00:00:00Z",
      formats: ["pdf", "ppt", "video"],
    });

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText(/PDF, Slides, Video/)).toBeInTheDocument();
    });
  });

  it("shows content tabs for complete job", async () => {
    mockFetchJob.mockResolvedValue({
      id: "job-456",
      filename: "lecture.pdf",
      status: "complete",
      stage: null,
      percent: 100,
      created_at: "2026-03-01T00:00:00Z",
      formats: ["pdf", "ppt", "video"],
    });

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
