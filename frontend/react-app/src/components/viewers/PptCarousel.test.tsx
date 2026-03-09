import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import PptCarousel from "./PptCarousel";

const mockFetchSlides = vi.fn();

vi.mock("@/api/jobs", () => ({
  fetchSlides: (...args: unknown[]) => mockFetchSlides(...args),
  viewSlideUrl: (jobId: string, index: number) => `/api/view/${jobId}/slide/${index}`,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PptCarousel", () => {
  it("shows loading state", () => {
    mockFetchSlides.mockReturnValue(new Promise(() => {}));
    renderWithProviders(<PptCarousel jobId="abc12345" />);
    expect(screen.getByText("Loading slides...")).toBeInTheDocument();
  });

  it("shows no slides message when empty", async () => {
    mockFetchSlides.mockResolvedValue({ slides: [], total: 0 });
    renderWithProviders(<PptCarousel jobId="abc12345" />);
    await waitFor(() => {
      expect(screen.getByText("No slides available")).toBeInTheDocument();
    });
  });

  it("renders slide image and counter", async () => {
    mockFetchSlides.mockResolvedValue({
      slides: ["/api/view/abc12345/slide/1", "/api/view/abc12345/slide/2", "/api/view/abc12345/slide/3"],
      total: 3,
    });
    renderWithProviders(<PptCarousel jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("slide-counter")).toHaveTextContent("1 / 3");
    });

    const img = screen.getByAltText("Slide 1 of 3");
    expect(img).toHaveAttribute("src", "/api/view/abc12345/slide/1");
  });

  it("navigates to next slide", async () => {
    mockFetchSlides.mockResolvedValue({
      slides: ["/api/view/abc12345/slide/1", "/api/view/abc12345/slide/2"],
      total: 2,
    });
    renderWithProviders(<PptCarousel jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("slide-counter")).toHaveTextContent("1 / 2");
    });

    fireEvent.click(screen.getByLabelText("Next slide"));

    expect(screen.getByTestId("slide-counter")).toHaveTextContent("2 / 2");
    expect(screen.getByAltText("Slide 2 of 2")).toHaveAttribute("src", "/api/view/abc12345/slide/2");
  });

  it("navigates to previous slide", async () => {
    mockFetchSlides.mockResolvedValue({
      slides: ["/api/view/abc12345/slide/1", "/api/view/abc12345/slide/2"],
      total: 2,
    });
    renderWithProviders(<PptCarousel jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("slide-counter")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("Next slide"));
    fireEvent.click(screen.getByLabelText("Previous slide"));

    expect(screen.getByTestId("slide-counter")).toHaveTextContent("1 / 2");
  });

  it("disables previous on first slide", async () => {
    mockFetchSlides.mockResolvedValue({
      slides: ["/api/view/abc12345/slide/1", "/api/view/abc12345/slide/2"],
      total: 2,
    });
    renderWithProviders(<PptCarousel jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByLabelText("Previous slide")).toBeDisabled();
    });
  });

  it("disables next on last slide", async () => {
    mockFetchSlides.mockResolvedValue({
      slides: ["/api/view/abc12345/slide/1"],
      total: 1,
    });
    renderWithProviders(<PptCarousel jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByLabelText("Next slide")).toBeDisabled();
    });
  });

  it("navigates with ArrowRight key", async () => {
    mockFetchSlides.mockResolvedValue({
      slides: ["/api/view/abc12345/slide/1", "/api/view/abc12345/slide/2"],
      total: 2,
    });
    renderWithProviders(<PptCarousel jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("slide-counter")).toHaveTextContent("1 / 2");
    });

    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(screen.getByTestId("slide-counter")).toHaveTextContent("2 / 2");
  });

  it("navigates with ArrowLeft key", async () => {
    mockFetchSlides.mockResolvedValue({
      slides: ["/api/view/abc12345/slide/1", "/api/view/abc12345/slide/2"],
      total: 2,
    });
    renderWithProviders(<PptCarousel jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("slide-counter")).toBeInTheDocument();
    });

    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(screen.getByTestId("slide-counter")).toHaveTextContent("1 / 2");
  });

  it("does not go below slide 1 with ArrowLeft", async () => {
    mockFetchSlides.mockResolvedValue({
      slides: ["/api/view/abc12345/slide/1", "/api/view/abc12345/slide/2"],
      total: 2,
    });
    renderWithProviders(<PptCarousel jobId="abc12345" />);

    await waitFor(() => {
      expect(screen.getByTestId("slide-counter")).toHaveTextContent("1 / 2");
    });

    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(screen.getByTestId("slide-counter")).toHaveTextContent("1 / 2");
  });
});
