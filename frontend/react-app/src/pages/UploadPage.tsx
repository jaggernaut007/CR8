/**
 * Upload page — drag-drop PDF/PPTX with format selection checkboxes.
 *
 * Uploads file to /api/upload, then starts pipeline via /api/start,
 * and navigates to the progress page.
 */

import { useState, useCallback, type DragEvent, type ChangeEvent } from "react";
import { useNavigate } from "react-router";
import { uploadFile, startPipeline } from "@/api/jobs";

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
];
const ACCEPTED_EXTENSIONS = [".pdf", ".pptx"];

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [formats, setFormats] = useState({ pdf: true, ppt: false, video: false });
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = (f: File): boolean => {
    const ext = f.name.toLowerCase().slice(f.name.lastIndexOf("."));
    if (!ACCEPTED_TYPES.includes(f.type) && !ACCEPTED_EXTENSIONS.includes(ext)) {
      setError("Only PDF and PPTX files are accepted");
      return false;
    }
    if (f.size > 50 * 1024 * 1024) {
      setError("File must be under 50 MB");
      return false;
    }
    setError(null);
    return true;
  };

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && validateFile(f)) setFile(f);
  }, []);

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f && validateFile(f)) setFile(f);
  };

  const handleFormatChange = (key: keyof typeof formats) => {
    setFormats((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      // Video auto-selects PPT (slides needed for video)
      if (key === "video" && next.video) next.ppt = true;
      // PDF is always on
      next.pdf = true;
      return next;
    });
  };

  const handleSubmit = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);

    try {
      // Step 1: Upload file
      const { job_id } = await uploadFile(file);

      // Step 2: Start pipeline
      const selectedFormats = Object.entries(formats)
        .filter(([, v]) => v)
        .map(([k]) => k);
      await startPipeline(job_id, selectedFormats);

      navigate(`/progress/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-8 text-2xl font-bold">New Generation</h1>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`glass glass-shadow cursor-pointer p-12 text-center transition ${
          isDragging ? "border-accent-blue bg-bg-glass-hover" : ""
        }`}
        onClick={() => document.getElementById("file-input")?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            document.getElementById("file-input")?.click();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Upload file"
      >
        <input
          id="file-input"
          type="file"
          accept=".pdf,.pptx"
          onChange={handleFileInput}
          className="hidden"
        />
        {file ? (
          <div>
            <p className="text-lg font-medium text-text-primary">{file.name}</p>
            <p className="mt-1 text-sm text-text-muted">
              {file.size < 1024 * 100
                ? `${(file.size / 1024).toFixed(0)} KB`
                : `${(file.size / 1024 / 1024).toFixed(1)} MB`}
            </p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              className="mt-3 text-sm text-accent-blue hover:underline"
            >
              Remove
            </button>
          </div>
        ) : (
          <div>
            <p className="text-lg text-text-secondary">
              Drop your PDF or PPTX here
            </p>
            <p className="mt-2 text-sm text-text-muted">or click to browse</p>
          </div>
        )}
      </div>

      {/* Format checkboxes */}
      <div className="mt-6 glass p-6">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-secondary">
          Output Formats
        </h3>
        <div className="flex gap-6">
          <FormatCheckbox label="PDF" checked={formats.pdf} disabled onChange={() => {}} />
          <FormatCheckbox
            label="Slides"
            checked={formats.ppt}
            onChange={() => handleFormatChange("ppt")}
          />
          <FormatCheckbox
            label="Video"
            checked={formats.video}
            onChange={() => handleFormatChange("video")}
          />
        </div>
      </div>

      {error && (
        <div className="mt-4 badge-error rounded-lg px-4 py-2.5 text-sm">
          {error}
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!file || isUploading}
        className="mt-6 w-full accent-gradient rounded-lg px-4 py-3 font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isUploading ? "Uploading..." : "Generate"}
      </button>
    </div>
  );
}

function FormatCheckbox({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm text-text-primary">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={onChange}
        className="h-4 w-4 rounded border-border-glass bg-bg-glass accent-accent-blue"
      />
      {label}
    </label>
  );
}
