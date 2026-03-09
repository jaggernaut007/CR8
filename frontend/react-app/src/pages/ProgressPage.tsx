/**
 * Progress page — shows pipeline stages, progress bar, and ETA.
 *
 * Polls /api/progress/{job_id} every 3 seconds. Stops polling on terminal
 * states (complete, error, cancelled). Redirects to results on completion.
 */

import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

interface ProgressData {
  status: string;
  stage: string;
  percent: number;
  logs: string[];
  elapsed: number;
  warnings: string[];
  eta_seconds?: number;
}

const STAGES = ["Ingest", "Research", "Generate", "Video"];

function stageStatus(currentStage: string, stage: string, percent: number): "done" | "active" | "pending" {
  const currentIdx = STAGES.indexOf(currentStage);
  const stageIdx = STAGES.indexOf(stage);
  if (stageIdx < currentIdx) return "done";
  if (stageIdx === currentIdx) return percent >= 100 ? "done" : "active";
  return "pending";
}

const TERMINAL_STATUSES = new Set(["complete", "error", "cancelled"]);

export default function ProgressPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [cancelError, setCancelError] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ["progress", jobId],
    queryFn: () => apiFetch<ProgressData>(`/api/progress/${jobId}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.has(status)) return false;
      return 3000;
    },
    enabled: !!jobId,
  });

  useEffect(() => {
    if (data?.status === "complete") {
      navigate(`/results/${jobId}`, { replace: true });
    }
  }, [data?.status, jobId, navigate]);

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  const handleCancel = async () => {
    try {
      await apiFetch(`/api/cancel/${jobId}`, { method: "POST" });
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : "Cancel failed");
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-8 text-2xl font-bold">Generating Content</h1>

      {/* Stage pipeline */}
      <div className="mb-8 flex gap-3">
        {STAGES.map((stage) => {
          const status = data ? stageStatus(data.stage, stage, data.percent) : "pending";
          return (
            <div
              key={stage}
              className={`glass flex-1 p-4 text-center transition ${
                status === "active" ? "border-accent-blue" : ""
              }`}
            >
              <div
                className={`mx-auto mb-2 h-3 w-3 rounded-full ${
                  status === "done"
                    ? "bg-success"
                    : status === "active"
                      ? "bg-accent-blue animate-pulse"
                      : "bg-bg-tertiary"
                }`}
              />
              <p
                className={`text-sm font-medium ${
                  status === "pending" ? "text-text-muted" : "text-text-primary"
                }`}
              >
                {stage}
              </p>
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="glass glass-shadow p-6">
        <div className="mb-2 flex justify-between text-sm">
          <span className="text-text-secondary">
            {data?.stage ?? "Starting"} &middot; {data?.percent ?? 0}%
          </span>
          {data?.eta_seconds != null && (
            <span className="text-text-muted">
              ETA: {formatTime(data.eta_seconds)}
            </span>
          )}
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-bg-tertiary">
          <div
            className="h-full accent-gradient transition-all duration-500 ease-out rounded-full"
            style={{ width: `${data?.percent ?? 0}%` }}
          />
        </div>
        {data?.elapsed != null && (
          <p className="mt-2 text-xs text-text-muted">
            Elapsed: {formatTime(data.elapsed)}
          </p>
        )}
      </div>

      {/* Warnings */}
      {data?.warnings && data.warnings.length > 0 && (
        <div className="mt-4 badge-warning rounded-lg p-4 text-sm">
          {data.warnings.map((w: string, i: number) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      {/* Error state */}
      {data?.status === "error" && (
        <div className="mt-4 badge-error rounded-lg p-4">
          <p className="font-medium">Pipeline failed</p>
          <button
            onClick={() => navigate("/upload")}
            className="mt-2 text-sm underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Cancel error */}
      {cancelError && (
        <div className="mt-4 badge-error rounded-lg px-4 py-2.5 text-sm">
          {cancelError}
        </div>
      )}

      {/* Cancel button */}
      {data?.status === "running" && (
        <button
          onClick={handleCancel}
          className="mt-6 w-full rounded-lg border border-border-glass bg-bg-glass px-4 py-2.5 text-sm text-text-secondary transition hover:bg-bg-glass-hover"
        >
          Stop Pipeline
        </button>
      )}
    </div>
  );
}
