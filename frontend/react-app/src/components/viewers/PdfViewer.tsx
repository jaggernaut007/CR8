/**
 * PDF viewer — renders a PDF inline using an iframe.
 * The browser's built-in PDF renderer handles display.
 */

import { viewPdfUrl } from "@/api/jobs";

interface PdfViewerProps {
  jobId: string;
}

export default function PdfViewer({ jobId }: PdfViewerProps) {
  return (
    <div className="w-full" data-testid="pdf-viewer">
      <iframe
        src={viewPdfUrl(jobId)}
        title="PDF Viewer"
        className="h-[600px] w-full rounded-lg border border-white/10"
      />
    </div>
  );
}
