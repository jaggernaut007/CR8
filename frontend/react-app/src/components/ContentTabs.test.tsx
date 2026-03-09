import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import ContentTabs from "./ContentTabs";

describe("ContentTabs", () => {
  it("always shows PDF tab", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="pdf" onTabChange={onTabChange} formats={["pdf"]} />,
    );
    expect(screen.getByText("PDF Guide")).toBeInTheDocument();
  });

  it("shows slides tab when ppt format present", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="pdf" onTabChange={onTabChange} formats={["pdf", "ppt"]} />,
    );
    expect(screen.getByText("Slides")).toBeInTheDocument();
  });

  it("shows video tab when video format present", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="pdf" onTabChange={onTabChange} formats={["pdf", "ppt", "video"]} />,
    );
    expect(screen.getByText("Video")).toBeInTheDocument();
  });

  it("hides slides tab when ppt not in formats", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="pdf" onTabChange={onTabChange} formats={["pdf"]} />,
    );
    expect(screen.queryByText("Slides")).not.toBeInTheDocument();
  });

  it("calls onTabChange when clicking a tab", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="pdf" onTabChange={onTabChange} formats={["pdf", "ppt"]} />,
    );
    fireEvent.click(screen.getByText("Slides"));
    expect(onTabChange).toHaveBeenCalledWith("ppt");
  });

  it("highlights active tab", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="ppt" onTabChange={onTabChange} formats={["pdf", "ppt"]} />,
    );
    const slidesTab = screen.getByText("Slides");
    expect(slidesTab).toHaveAttribute("aria-selected", "true");
  });

  // --- Additional edge cases ---

  it("inactive tab has aria-selected false", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="ppt" onTabChange={onTabChange} formats={["pdf", "ppt"]} />,
    );
    const pdfTab = screen.getByText("PDF Guide");
    expect(pdfTab).toHaveAttribute("aria-selected", "false");
  });

  it("tabs have role='tab'", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="pdf" onTabChange={onTabChange} formats={["pdf", "ppt"]} />,
    );
    const tabs = screen.getAllByRole("tab");
    expect(tabs.length).toBeGreaterThan(0);
  });

  it("still shows PDF tab when formats array is empty", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="pdf" onTabChange={onTabChange} formats={[]} />,
    );
    expect(screen.getByText("PDF Guide")).toBeInTheDocument();
  });

  it("hides video tab when video not in formats", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="pdf" onTabChange={onTabChange} formats={["pdf", "ppt"]} />,
    );
    expect(screen.queryByText("Video")).not.toBeInTheDocument();
  });

  it("calls onTabChange with correct key for video tab", () => {
    const onTabChange = vi.fn();
    renderWithProviders(
      <ContentTabs activeTab="pdf" onTabChange={onTabChange} formats={["pdf", "video"]} />,
    );
    fireEvent.click(screen.getByText("Video"));
    expect(onTabChange).toHaveBeenCalledWith("video");
  });
});
