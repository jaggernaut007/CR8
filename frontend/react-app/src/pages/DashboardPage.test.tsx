import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders, resetMockAuth } from "@/test/test-utils";
import DashboardPage from "./DashboardPage";

vi.mock("@/api/jobs", () => ({
  fetchJobs: vi.fn(),
  startPipeline: vi.fn(),
}));

import { fetchJobs, startPipeline } from "@/api/jobs";
const mockFetchJobs = vi.mocked(fetchJobs);
const mockStartPipeline = vi.mocked(startPipeline);

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

beforeEach(() => {
  resetMockAuth();
  vi.clearAllMocks();
  mockStartPipeline.mockResolvedValue({ status: "running" });
  mockNavigate.mockClear();
});

describe("DashboardPage", () => {
  it("shows loading state", () => {
    mockFetchJobs.mockReturnValue(new Promise(() => {})); // never resolves
    renderWithProviders(<DashboardPage />);
    expect(screen.getByText("Loading jobs...")).toBeInTheDocument();
  });

  it("shows empty state when no jobs", async () => {
    mockFetchJobs.mockResolvedValue({ jobs: [], total: 0 });
    renderWithProviders(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("No generations yet")).toBeInTheDocument();
    });
  });

  it("renders job list", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-1",
          filename: "lecture.pdf",
          status: "complete",
          stage: null,
          percent: 100,
          created_at: "2026-03-01T00:00:00Z",
          formats: ["pdf", "ppt"],
        },
        {
          id: "job-2",
          filename: "notes.pdf",
          status: "running",
          stage: "Research",
          percent: 45,
          created_at: "2026-03-02T00:00:00Z",
          formats: ["pdf"],
        },
      ],
      total: 2,
    });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("lecture.pdf")).toBeInTheDocument();
      expect(screen.getByText("notes.pdf")).toBeInTheDocument();
    });

    expect(screen.getByText("Complete")).toBeInTheDocument();
    expect(screen.getByText("Running 45%")).toBeInTheDocument();
  });

  it("shows error state", async () => {
    mockFetchJobs.mockRejectedValue(new Error("Network error"));
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load jobs. Please try again.")).toBeInTheDocument();
    });
  });

  it("has new generation link", async () => {
    mockFetchJobs.mockResolvedValue({ jobs: [], total: 0 });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("+ New Generation")).toBeInTheDocument();
    });
  });

  it("renders cancelled status badge", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-3",
          filename: "cancelled.pdf",
          status: "cancelled",
          stage: null,
          percent: 0,
          created_at: "2026-03-03T00:00:00Z",
          formats: ["pdf"],
        },
      ],
      total: 1,
    });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Cancelled")).toBeInTheDocument();
    });
  });
});

// ── JobCard re-run button tests ───────────────────────────────────────────────

describe("DashboardPage — Re-run button", () => {
  it("shows Re-run button for error jobs", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-err",
          filename: "failed.pdf",
          status: "error",
          stage: null,
          percent: 0,
          created_at: "2026-03-01T00:00:00Z",
          formats: ["pdf"],
        },
      ],
      total: 1,
    });

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByTestId("rerun-btn")).toBeInTheDocument();
    });

    expect(screen.getByTestId("rerun-btn")).toHaveTextContent("Re-run");
  });

  it("shows Re-run button for cancelled jobs", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-can",
          filename: "cancelled.pdf",
          status: "cancelled",
          stage: null,
          percent: 0,
          created_at: "2026-03-01T00:00:00Z",
          formats: ["pdf"],
        },
      ],
      total: 1,
    });

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByTestId("rerun-btn")).toBeInTheDocument();
    });
  });

  it("does not show Re-run button for complete jobs", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-ok",
          filename: "done.pdf",
          status: "complete",
          stage: null,
          percent: 100,
          created_at: "2026-03-01T00:00:00Z",
          formats: ["pdf"],
        },
      ],
      total: 1,
    });

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("done.pdf")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("rerun-btn")).not.toBeInTheDocument();
  });

  it("does not show Re-run button for running jobs", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-run",
          filename: "running.pdf",
          status: "running",
          stage: "Research",
          percent: 40,
          created_at: "2026-03-01T00:00:00Z",
          formats: ["pdf"],
        },
      ],
      total: 1,
    });

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("running.pdf")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("rerun-btn")).not.toBeInTheDocument();
  });

  it("clicking Re-run calls startPipeline with the job's formats", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-rerun",
          filename: "retry.pdf",
          status: "error",
          stage: null,
          percent: 0,
          created_at: "2026-03-01T00:00:00Z",
          formats: ["pdf", "ppt"],
        },
      ],
      total: 1,
    });
    // Keep pending so navigation doesn't fire during assertion
    mockStartPipeline.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByTestId("rerun-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("rerun-btn"));

    await waitFor(() => {
      expect(mockStartPipeline).toHaveBeenCalledWith("job-rerun", ["pdf", "ppt"]);
    });
  });

  it("navigates to /progress/:jobId after successful re-run", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-nav",
          filename: "retry.pdf",
          status: "error",
          stage: null,
          percent: 0,
          created_at: "2026-03-01T00:00:00Z",
          formats: ["pdf"],
        },
      ],
      total: 1,
    });
    mockStartPipeline.mockResolvedValue({ status: "running" });

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByTestId("rerun-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("rerun-btn"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/progress/job-nav");
    });
  });

  it("shows 'Starting...' text while re-run mutation is pending", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-pend",
          filename: "pending.pdf",
          status: "cancelled",
          stage: null,
          percent: 0,
          created_at: "2026-03-01T00:00:00Z",
          formats: ["pdf"],
        },
      ],
      total: 1,
    });
    mockStartPipeline.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByTestId("rerun-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("rerun-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("rerun-btn")).toHaveTextContent("Starting...");
    });
  });

  it("button is disabled while re-run mutation is pending", async () => {
    mockFetchJobs.mockResolvedValue({
      jobs: [
        {
          id: "job-dis",
          filename: "pending.pdf",
          status: "error",
          stage: null,
          percent: 0,
          created_at: "2026-03-01T00:00:00Z",
          formats: ["pdf"],
        },
      ],
      total: 1,
    });
    mockStartPipeline.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByTestId("rerun-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("rerun-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("rerun-btn")).toBeDisabled();
    });
  });
});
