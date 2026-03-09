import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders, resetMockAuth } from "@/test/test-utils";
import DashboardPage from "./DashboardPage";

vi.mock("@/api/jobs", () => ({
  fetchJobs: vi.fn(),
}));

import { fetchJobs } from "@/api/jobs";
const mockFetchJobs = vi.mocked(fetchJobs);

beforeEach(() => {
  resetMockAuth();
  vi.clearAllMocks();
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
