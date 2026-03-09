import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import VideoPlayer from "./VideoPlayer";

const mockFetchVideos = vi.fn();

vi.mock("@/api/jobs", () => ({
  fetchVideos: (...args: unknown[]) => mockFetchVideos(...args),
  viewVideoUrl: (jobId: string, index: number) => `/api/view/${jobId}/video/${index}`,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("VideoPlayer", () => {
  it("shows loading state", () => {
    mockFetchVideos.mockReturnValue(new Promise(() => {}));
    renderWithProviders(<VideoPlayer jobId="abc12345" />);
    expect(screen.getByText("Loading videos...")).toBeInTheDocument();
  });

  it("shows no videos message when empty", async () => {
    mockFetchVideos.mockResolvedValue({ videos: [] });
    renderWithProviders(<VideoPlayer jobId="abc12345" />);
    await waitFor(() => {
      expect(screen.getByText("No videos available")).toBeInTheDocument();
    });
  });

  it("renders video element with single video", async () => {
    mockFetchVideos.mockResolvedValue({
      videos: [{ name: "Introduction", url: "/api/view/abc12345/video/0" }],
    });
    renderWithProviders(<VideoPlayer jobId="abc12345" />);

    await waitFor(() => {
      const video = document.querySelector("video");
      expect(video).toBeInTheDocument();
      expect(video).toHaveAttribute("src", "/api/view/abc12345/video/0");
    });

    expect(screen.getByText("Introduction")).toBeInTheDocument();
  });

  it("shows topic selector with multiple videos", async () => {
    mockFetchVideos.mockResolvedValue({
      videos: [
        { name: "Introduction", url: "/api/view/abc12345/video/0" },
        { name: "Advanced Topics", url: "/api/view/abc12345/video/1" },
      ],
    });
    renderWithProviders(<VideoPlayer jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("video-selector")).toBeInTheDocument();
    });

    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent("Introduction");
    expect(options[1]).toHaveTextContent("Advanced Topics");
  });

  it("switches video on topic change", async () => {
    mockFetchVideos.mockResolvedValue({
      videos: [
        { name: "Introduction", url: "/api/view/abc12345/video/0" },
        { name: "Advanced", url: "/api/view/abc12345/video/1" },
      ],
    });
    renderWithProviders(<VideoPlayer jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("video-selector")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("video-selector"), { target: { value: "1" } });

    const video = document.querySelector("video");
    expect(video).toHaveAttribute("src", "/api/view/abc12345/video/1");
  });

  it("hides selector for single video", async () => {
    mockFetchVideos.mockResolvedValue({
      videos: [{ name: "Solo Video", url: "/api/view/abc12345/video/0" }],
    });
    renderWithProviders(<VideoPlayer jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("video-player")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("video-selector")).not.toBeInTheDocument();
  });

  // --- Additional edge cases ---

  it("shows no videos message on fetch error", async () => {
    mockFetchVideos.mockRejectedValue(new Error("Network error"));
    renderWithProviders(<VideoPlayer jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByText("No videos available")).toBeInTheDocument();
    });
  });

  it("video element has controls attribute", async () => {
    mockFetchVideos.mockResolvedValue({
      videos: [{ name: "Introduction", url: "/api/view/abc12345/video/0" }],
    });
    renderWithProviders(<VideoPlayer jobId="abc12345" />);

    await waitFor(() => {
      const video = document.querySelector("video");
      expect(video).toHaveAttribute("controls");
    });
  });

  it("does not show video name label for multiple videos", async () => {
    mockFetchVideos.mockResolvedValue({
      videos: [
        { name: "Introduction", url: "/api/view/abc12345/video/0" },
        { name: "Advanced Topics", url: "/api/view/abc12345/video/1" },
      ],
    });
    renderWithProviders(<VideoPlayer jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("video-selector")).toBeInTheDocument();
    });

    // The name label under the video element is only shown for single videos
    const videoPlayer = screen.getByTestId("video-player");
    const nameLabel = videoPlayer.querySelector("p");
    expect(nameLabel).not.toBeInTheDocument();
  });
});
