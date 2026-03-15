/**
 * Dashboard — shows job history with status badges and "New Generation" CTA.
 *
 * Uses Tanstack Query to fetch jobs from the API with automatic refetching.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { fetchJobs, startPipeline, type Job } from "@/api/jobs";

function statusBadgeClass(status: string): string {
  switch (status) {
    case "complete":
      return "badge-success";
    case "running":
      return "badge-warning";
    case "error":
    case "cancelled":
      return "badge-error";
    case "pending":
      return "bg-accent-blue/20 text-accent-blue";
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
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => fetchJobs(),
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
            Upload a curriculum PDF/PPTX to get started
          </p>
          <Link
            to="/upload"
            className="mt-6 inline-block accent-gradient rounded-lg px-6 py-2.5 font-medium text-white transition hover:opacity-90"
          >
            Upload PDF/PPTX
          </Link>
        </div>
      )}

      {data && data.jobs.length > 0 && (
        <div className="space-y-3">
          {data.jobs.map((job) => (
            <JobCard key={job.id} job={job} navigate={navigate} queryClient={queryClient} />
          ))}
        </div>
      )}
    </div>
  );
}

function JobCard({
  job,
  navigate,
  queryClient,
}: {
  job: Job;
  navigate: (path: string) => void;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const rerunMutation = useMutation({
    mutationFn: () => startPipeline(job.id, job.formats),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      navigate(`/progress/${job.id}`);
    },
  });

  const canRerun = job.status === "error" || job.status === "cancelled" || job.status === "pending";
  const rerunLabel = job.status === "pending" ? "Resume" : "Re-run";
  const linkTo = job.status === "running" ? `/progress/${job.id}` : `/results/${job.id}`;

  return (
    <div className="glass flex items-center justify-between p-4 transition hover:glass-hover">
      <Link to={linkTo} className="flex-1">
        <p className="font-medium text-text-primary">{job.filename}</p>
        <p className="mt-1 text-xs text-text-muted">
          {new Date(job.created_at).toLocaleDateString()} &middot;{" "}
          {job.formats.join(", ").toUpperCase()}
        </p>
      </Link>
      <div className="flex items-center gap-3">
        {canRerun && (
          <button
            onClick={(e) => {
              e.preventDefault();
              rerunMutation.mutate();
            }}
            disabled={rerunMutation.isPending}
            className="rounded-md bg-accent-blue/20 px-3 py-1 text-xs font-medium text-accent-blue transition hover:bg-accent-blue/30 disabled:opacity-40"
            data-testid="rerun-btn"
          >
            {rerunMutation.isPending ? "Starting..." : rerunLabel}
          </button>
        )}
        {rerunMutation.isError && (
          <span className="text-xs text-error">Upload expired — re-upload file</span>
        )}
        <StatusBadge status={job.status} percent={job.percent} />
      </div>
    </div>
  );
}
