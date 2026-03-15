/**
 * Results page — shows completion status, content viewers, and download buttons.
 *
 * Content viewers: PDF (iframe), Slides (image carousel), Video (HTML5 player).
 * Download buttons link to /api/download/:jobId/:type.
 */

import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchJob, startPipeline, downloadUrl, type Job } from "@/api/jobs";
import { fetchQuizzesByJob, generateQuiz } from "@/api/quiz";
import ContentTabs from "@/components/ContentTabs";
import PdfViewer from "@/components/viewers/PdfViewer";
import PptCarousel from "@/components/viewers/PptCarousel";
import VideoPlayer from "@/components/viewers/VideoPlayer";

const DOWNLOAD_TYPES: { key: string; label: string; icon: string }[] = [
  { key: "pdf", label: "Learning Guide", icon: "PDF" },
  { key: "ppt", label: "Slide Deck", icon: "PPT" },
  { key: "scripts", label: "Video Scripts", icon: "TXT" },
  { key: "videos", label: "Videos", icon: "MP4" },
];

function formatLabel(format: string): string {
  switch (format) {
    case "pdf": return "PDF";
    case "ppt": return "Slides";
    case "video": return "Video";
    default: return format.toUpperCase();
  }
}

/** Trigger a file download via browser navigation. Auth is handled by same-origin cookies. */
function triggerDownload(url: string): void {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.setAttribute("download", "");
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("pdf");

  const { data: job, isLoading, error } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => fetchJob(jobId!),
    enabled: !!jobId,
  });

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {isLoading && (
        <div className="glass p-12 text-center text-text-secondary">
          Loading results...
        </div>
      )}

      {error && (
        <div className="badge-error rounded-lg p-4 text-sm">
          <p>Failed to load job details.</p>
          <Link to="/dashboard" className="mt-2 inline-block underline">
            Back to Dashboard
          </Link>
        </div>
      )}

      {job && (
        <>
          {/* Header */}
          <div className="glass glass-shadow p-8 text-center">
            <StatusIcon status={job.status} />

            <h1 className="mb-2 text-2xl font-bold">
              {job.status === "complete" ? "Generation Complete" : `Job ${job.status}`}
            </h1>
            <p className="text-text-secondary">{job.filename}</p>
            <p className="mt-1 text-xs text-text-muted">
              {new Date(job.created_at).toLocaleDateString()} &middot;{" "}
              {job.formats.map(formatLabel).join(", ")}
            </p>
          </div>

          {/* Content viewers (only for complete jobs) */}
          {job.status === "complete" && (
            <div className="mt-6 space-y-4">
              <ContentTabs
                activeTab={activeTab}
                onTabChange={setActiveTab}
                formats={job.formats}
              />

              <div className="glass glass-shadow rounded-lg p-4">
                {activeTab === "pdf" && <PdfViewer jobId={jobId!} />}
                {activeTab === "ppt" && <PptCarousel jobId={jobId!} />}
                {activeTab === "video" && <VideoPlayer jobId={jobId!} />}
              </div>
            </div>
          )}

          {/* Download buttons */}
          {job.status === "complete" && (
            <div className="mt-6 space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
                Downloads
              </h2>
              <div className="grid grid-cols-2 gap-3">
                {availableDownloads(job).map(({ key, label, icon }) => (
                  <button
                    key={key}
                    onClick={() => triggerDownload(downloadUrl(jobId!, key))}
                    className="glass flex items-center gap-3 p-4 transition hover:glass-hover"
                  >
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-blue/20 text-xs font-bold text-accent-blue">
                      {icon}
                    </span>
                    <span className="text-sm font-medium text-text-primary">{label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Add Video option (only when video wasn't generated) */}
          {job.status === "complete" && !job.formats.includes("video") && (
            <AddVideoSection jobId={jobId!} formats={job.formats} navigate={navigate} />
          )}

          {/* Quiz section (only for complete jobs) */}
          {job.status === "complete" && (
            <QuizSection jobId={jobId!} navigate={navigate} />
          )}

          {/* Back to dashboard */}
          <Link
            to="/dashboard"
            className="mt-6 inline-block accent-gradient rounded-lg px-6 py-2.5 font-medium text-white transition hover:opacity-90"
          >
            Back to Dashboard
          </Link>
        </>
      )}
    </div>
  );
}

/** Filter download types based on which formats the job was configured with. */
function availableDownloads(job: Job) {
  return DOWNLOAD_TYPES.filter(({ key }) => {
    if (key === "pdf") return true; // PDF guide is always generated
    if (key === "ppt") return job.formats.includes("ppt");
    if (key === "scripts" || key === "videos") return job.formats.includes("video");
    return false;
  });
}

function AddVideoSection({
  jobId,
  formats,
  navigate,
}: {
  jobId: string;
  formats: string[];
  navigate: (path: string) => void;
}) {
  const mutation = useMutation({
    mutationFn: () => {
      const newFormats = [...new Set([...formats, "ppt", "video"])];
      return startPipeline(jobId, newFormats);
    },
    onSuccess: () => navigate(`/progress/${jobId}`),
  });

  return (
    <div className="mt-6 space-y-3" data-testid="add-video-section">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
        Video
      </h2>
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="glass w-full p-4 text-center text-sm font-medium transition hover:glass-hover disabled:opacity-40"
        data-testid="generate-video-btn"
      >
        {mutation.isPending ? "Starting Video Generation..." : "Generate Video"}
      </button>
      {mutation.isError && (
        <div className="badge-error rounded-lg p-3 text-sm">
          Failed to start video generation.
        </div>
      )}
    </div>
  );
}

function QuizSection({ jobId, navigate }: { jobId: string; navigate: (path: string) => void }) {
  const { data: quizList } = useQuery({
    queryKey: ["quizzesByJob", jobId],
    queryFn: () => fetchQuizzesByJob(jobId),
  });

  const genMutation = useMutation({
    mutationFn: () => generateQuiz(jobId),
    onSuccess: (data) => navigate(`/quiz/${data.quiz_id}`),
  });

  const quizzes = quizList?.quizzes ?? [];

  return (
    <div className="mt-6 space-y-3" data-testid="quiz-section">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
        Quiz
      </h2>
      {quizzes.length === 0 ? (
        <button
          onClick={() => genMutation.mutate()}
          disabled={genMutation.isPending}
          className="glass w-full p-4 text-center text-sm font-medium transition hover:glass-hover disabled:opacity-40"
          data-testid="generate-quiz-btn"
        >
          {genMutation.isPending ? "Generating Quiz..." : "Generate Quiz"}
        </button>
      ) : (
        <div className="space-y-2">
          {quizzes.map((q, i) => (
            <Link
              key={q.id}
              to={`/quiz/${q.id}`}
              className="glass flex items-center justify-between p-4 transition hover:glass-hover"
              data-testid="quiz-link"
            >
              <div>
                <span className="text-sm font-medium text-text-primary">{q.title}</span>
                {quizzes.length > 1 && (
                  <span className="ml-2 text-xs text-text-muted">
                    (Attempt {i + 1})
                  </span>
                )}
              </div>
              <span className="text-xs text-text-muted">Take Quiz</span>
            </Link>
          ))}
        </div>
      )}
      {genMutation.isError && (
        <div className="badge-error rounded-lg p-3 text-sm">
          Failed to generate quiz.
        </div>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "complete") {
    return (
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-success/20">
        <svg className="h-8 w-8 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-error/20">
        <svg className="h-8 w-8 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
    );
  }
  return (
    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-bg-tertiary">
      <svg className="h-8 w-8 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01" />
      </svg>
    </div>
  );
}
