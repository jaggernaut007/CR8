import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders, resetMockAuth } from "@/test/test-utils";
import ProgressPage from "./ProgressPage";

vi.mock("@/api/jobs", () => ({
  fetchProgress: vi.fn(),
  cancelJob: vi.fn(),
}));

import { fetchProgress, cancelJob } from "@/api/jobs";
const mockFetchProgress = vi.mocked(fetchProgress);
const mockCancelJob = vi.mocked(cancelJob);

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ jobId: "job-123" }),
  };
});

beforeEach(() => {
  resetMockAuth();
  vi.clearAllMocks();
});

describe("ProgressPage", () => {
  it("renders page title and stages", async () => {
    mockFetchProgress.mockResolvedValue({
      status: "running",
      stage: "Research",
      percent: 45,
      logs: [],
      elapsed: 60,
      warnings: [],
    });

    renderWithProviders(<ProgressPage />);
    expect(screen.getByText("Generating Content")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Ingest")).toBeInTheDocument();
      expect(screen.getByText("Research")).toBeInTheDocument();
      expect(screen.getByText("Generate")).toBeInTheDocument();
      expect(screen.getByText("Video")).toBeInTheDocument();
    });
  });

  it("shows progress percentage and elapsed time", async () => {
    mockFetchProgress.mockResolvedValue({
      status: "running",
      stage: "Generate",
      percent: 67,
      logs: [],
      elapsed: 120,
      warnings: [],
    });

    renderWithProviders(<ProgressPage />);

    await waitFor(() => {
      expect(screen.getByText(/67%/)).toBeInTheDocument();
      expect(screen.getByText("Elapsed: 2m 0s")).toBeInTheDocument();
    });
  });

  it("shows ETA when available", async () => {
    mockFetchProgress.mockResolvedValue({
      status: "running",
      stage: "Research",
      percent: 30,
      logs: [],
      elapsed: 60,
      warnings: [],
      eta_seconds: 90,
    });

    renderWithProviders(<ProgressPage />);

    await waitFor(() => {
      expect(screen.getByText("ETA: 1m 30s")).toBeInTheDocument();
    });
  });

  it("shows cancel button when running", async () => {
    mockFetchProgress.mockResolvedValue({
      status: "running",
      stage: "Research",
      percent: 30,
      logs: [],
      elapsed: 60,
      warnings: [],
    });

    renderWithProviders(<ProgressPage />);

    await waitFor(() => {
      expect(screen.getByText("Stop Pipeline")).toBeInTheDocument();
    });
  });

  it("calls cancelJob when stop is clicked", async () => {
    mockCancelJob.mockResolvedValue({ status: "cancelled" });
    mockFetchProgress.mockResolvedValue({
      status: "running",
      stage: "Research",
      percent: 30,
      logs: [],
      elapsed: 60,
      warnings: [],
    });

    renderWithProviders(<ProgressPage />);

    await waitFor(() => {
      expect(screen.getByText("Stop Pipeline")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Stop Pipeline"));

    await waitFor(() => {
      expect(mockCancelJob).toHaveBeenCalledWith("job-123");
    });
  });

  it("shows error state with retry link", async () => {
    mockFetchProgress.mockResolvedValue({
      status: "error",
      stage: "Generate",
      percent: 50,
      logs: [],
      elapsed: 180,
      warnings: [],
    });

    renderWithProviders(<ProgressPage />);

    await waitFor(() => {
      expect(screen.getByText("Pipeline failed")).toBeInTheDocument();
      expect(screen.getByText("Try again")).toBeInTheDocument();
    });
  });

  it("shows warnings", async () => {
    mockFetchProgress.mockResolvedValue({
      status: "running",
      stage: "Video",
      percent: 80,
      logs: [],
      elapsed: 300,
      warnings: ["GPU unavailable, using CPU fallback"],
    });

    renderWithProviders(<ProgressPage />);

    await waitFor(() => {
      expect(screen.getByText("GPU unavailable, using CPU fallback")).toBeInTheDocument();
    });
  });

  it("shows cancel error on failure", async () => {
    mockCancelJob.mockRejectedValue(new Error("Cancel denied"));
    mockFetchProgress.mockResolvedValue({
      status: "running",
      stage: "Research",
      percent: 30,
      logs: [],
      elapsed: 60,
      warnings: [],
    });

    renderWithProviders(<ProgressPage />);

    await waitFor(() => {
      expect(screen.getByText("Stop Pipeline")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Stop Pipeline"));

    await waitFor(() => {
      expect(screen.getByText("Cancel denied")).toBeInTheDocument();
    });
  });

  it("navigates to results on completion", async () => {
    mockFetchProgress.mockResolvedValue({
      status: "complete",
      stage: "Video",
      percent: 100,
      logs: [],
      elapsed: 600,
      warnings: [],
    });

    renderWithProviders(<ProgressPage />);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/results/job-123", { replace: true });
    });
  });
});
