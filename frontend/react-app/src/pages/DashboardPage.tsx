/**
 * Dashboard — shows job history with status badges and "New Generation" CTA.
 *
 * Uses Tanstack Query to fetch jobs from the API with automatic refetching.
 */

import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { apiFetch } from "@/api/client";

interface Job {
  id: string;
  filename: string;
  status: string;
  stage: string | null;
  percent: number;
  created_at: string;
  formats: string[];
}

interface JobsResponse {
  jobs: Job[];
  total: number;
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "complete":
      return "badge-success";
    case "running":
      return "badge-warning";
    case "error":
    case "cancelled":
      return "badge-error";
    default:
      return "bg-bg-tertiary text-text-secondary";
  }
}

function StatusBadge({ status, percent }: { status: string; percent: number }) {
  const label =
    status === "running" ? `Running ${percent}%` : status.charAt(0).toUpperCase() + status.slice(1);
  return (
    <span
      className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${statusBadgeClass(status)}`}
    >
      {label}
    </span>
  );
}

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => apiFetch<JobsResponse>("/api/jobs?limit=20&offset=0"),
    refetchInterval: 10000,
  });

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Your Generations</h1>
        <Link
          to="/upload"
          className="accent-gradient rounded-lg px-5 py-2.5 font-medium text-white transition hover:opacity-90"
        >
          + New Generation
        </Link>
      </div>

      {isLoading && (
        <div className="glass p-12 text-center text-text-secondary">
          Loading jobs...
        </div>
      )}

      {error && (
        <div className="badge-error rounded-lg p-4 text-sm">
          Failed to load jobs. Please try again.
        </div>
      )}

      {data && data.jobs.length === 0 && (
        <div className="glass glass-shadow p-12 text-center">
          <p className="text-lg text-text-secondary">No generations yet</p>
          <p className="mt-2 text-sm text-text-muted">
            Upload a curriculum PDF to get started
          </p>
          <Link
            to="/upload"
            className="mt-6 inline-block accent-gradient rounded-lg px-6 py-2.5 font-medium text-white transition hover:opacity-90"
          >
            Upload PDF
          </Link>
        </div>
      )}

      {data && data.jobs.length > 0 && (
        <div className="space-y-3">
          {data.jobs.map((job) => (
            <Link
              key={job.id}
              to={job.status === "running" ? `/progress/${job.id}` : `/results/${job.id}`}
              className="glass flex items-center justify-between p-4 transition hover:glass-hover"
            >
              <div>
                <p className="font-medium text-text-primary">{job.filename}</p>
                <p className="mt-1 text-xs text-text-muted">
                  {new Date(job.created_at).toLocaleDateString()} &middot;{" "}
                  {job.formats.join(", ").toUpperCase()}
                </p>
              </div>
              <StatusBadge status={job.status} percent={job.percent} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
