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
});
