import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import PdfViewer from "./PdfViewer";

describe("PdfViewer", () => {
  it("renders an iframe with correct src", () => {
    renderWithProviders(<PdfViewer jobId="abc12345" />);
    const iframe = screen.getByTitle("PDF Viewer");
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute("src", "/api/view/abc12345/pdf");
  });

  it("has data-testid for E2E targeting", () => {
    renderWithProviders(<PdfViewer jobId="abc12345" />);
    expect(screen.getByTestId("pdf-viewer")).toBeInTheDocument();
  });
});
