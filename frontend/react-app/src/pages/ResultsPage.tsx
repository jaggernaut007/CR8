/**
 * Results page stub — placeholder until Wave 2 builds content viewers.
 *
 * Shows job completion status and links back to dashboard.
 * Will be replaced with PDF viewer, PPT carousel, video player, and download buttons.
 */

import { useParams, Link } from "react-router";

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="glass glass-shadow p-8 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-success/20">
          <svg
            className="h-8 w-8 text-success"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <h1 className="mb-2 text-2xl font-bold">Generation Complete</h1>
        <p className="text-text-secondary">
          Job <span className="font-mono text-text-primary">{jobId}</span> finished
          successfully.
        </p>

        <p className="mt-6 text-sm text-text-muted">
          Content viewers and download buttons are coming in Wave 2.
        </p>

        <Link
          to="/dashboard"
          className="mt-6 inline-block accent-gradient rounded-lg px-6 py-2.5 font-medium text-white transition hover:opacity-90"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
