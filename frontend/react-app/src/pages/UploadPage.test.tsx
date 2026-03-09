import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders, resetMockAuth } from "@/test/test-utils";
import UploadPage from "./UploadPage";

vi.mock("@/api/jobs", () => ({
  uploadFile: vi.fn(),
  startPipeline: vi.fn(),
}));

import { uploadFile, startPipeline } from "@/api/jobs";
const mockUpload = vi.mocked(uploadFile);
const mockStart = vi.mocked(startPipeline);

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return { ...actual, useNavigate: () => mockNavigate };
});

beforeEach(() => {
  resetMockAuth();
  vi.clearAllMocks();
});

function createFile(name: string, size: number, type: string): File {
  const buffer = new ArrayBuffer(size);
  return new File([buffer], name, { type });
}

describe("UploadPage", () => {
  it("renders drop zone and format checkboxes", () => {
    renderWithProviders(<UploadPage />);
    expect(screen.getByText("Drop your PDF or PPTX here")).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
    expect(screen.getByText("Slides")).toBeInTheDocument();
    expect(screen.getByText("Video")).toBeInTheDocument();
  });

  it("PDF checkbox is always checked and disabled", () => {
    renderWithProviders(<UploadPage />);
    const pdfCheckbox = screen.getByRole("checkbox", { name: "PDF" });
    expect(pdfCheckbox).toBeChecked();
    expect(pdfCheckbox).toBeDisabled();
  });

  it("shows file info after selection via input", () => {
    renderWithProviders(<UploadPage />);
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    const file = createFile("test.pdf", 1024 * 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByText("test.pdf")).toBeInTheDocument();
    expect(screen.getByText("1.0 MB")).toBeInTheDocument();
  });

  it("rejects files over 50 MB", () => {
    renderWithProviders(<UploadPage />);
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    const bigFile = createFile("big.pdf", 51 * 1024 * 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [bigFile] } });
    expect(screen.getByText("File must be under 50 MB")).toBeInTheDocument();
  });

  it("rejects non-PDF/PPTX files", () => {
    renderWithProviders(<UploadPage />);
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    const txtFile = createFile("notes.txt", 1024, "text/plain");
    fireEvent.change(input, { target: { files: [txtFile] } });
    expect(screen.getByText("Only PDF and PPTX files are accepted")).toBeInTheDocument();
  });

  it("uploads and starts pipeline on submit", async () => {
    mockUpload.mockResolvedValue({ job_id: "job-123", filename: "test.pdf" });
    mockStart.mockResolvedValue({ status: "running" });

    renderWithProviders(<UploadPage />);

    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    const file = createFile("test.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByText("Generate"));

    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalled();
      expect(mockStart).toHaveBeenCalledWith("job-123", ["pdf"]);
      expect(mockNavigate).toHaveBeenCalledWith("/progress/job-123");
    });
  });

  it("shows error on upload failure", async () => {
    mockUpload.mockRejectedValue(new Error("Server error"));

    renderWithProviders(<UploadPage />);

    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    const file = createFile("test.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByText("Generate"));

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("auto-selects PPT when Video is checked", () => {
    renderWithProviders(<UploadPage />);
    const videoCheckbox = screen.getByRole("checkbox", { name: "Video" });
    const slidesCheckbox = screen.getByRole("checkbox", { name: "Slides" });

    fireEvent.click(videoCheckbox);
    expect(slidesCheckbox).toBeChecked();
    expect(videoCheckbox).toBeChecked();
  });

  it("generate button is disabled without file", () => {
    renderWithProviders(<UploadPage />);
    expect(screen.getByText("Generate")).toBeDisabled();
  });

  it("accepts file via drag and drop", () => {
    renderWithProviders(<UploadPage />);
    const dropZone = screen.getByRole("button", { name: "Upload file" });
    const file = createFile("dropped.pdf", 2048, "application/pdf");

    fireEvent.dragOver(dropZone, { preventDefault: vi.fn() });
    fireEvent.drop(dropZone, {
      preventDefault: vi.fn(),
      dataTransfer: { files: [file] },
    });

    expect(screen.getByText("dropped.pdf")).toBeInTheDocument();
  });

  it("shows remove button after file selection", () => {
    renderWithProviders(<UploadPage />);
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    const file = createFile("test.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });

    const removeButton = screen.getByText("Remove");
    expect(removeButton).toBeInTheDocument();

    fireEvent.click(removeButton);
    expect(screen.getByText("Drop your PDF or PPTX here")).toBeInTheDocument();
  });
});
