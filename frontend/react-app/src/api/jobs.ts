/**
 * Job API — typed functions for upload, pipeline control, progress, and downloads.
 *
 * All job-related types and API calls live here. Pages import from this module
 * instead of defining inline interfaces.
 */

import { apiFetch } from "./client";

// ── Types ──────────────────────────────────────────────────────────────

export interface Job {
  id: string;
  filename: string;
  status: string;
  stage: string | null;
  percent: number;
  created_at: string;
  formats: string[];
}

export interface JobsResponse {
  jobs: Job[];
  total: number;
}

export interface UploadResponse {
  job_id: string;
  filename: string;
}

export interface ProgressData {
  status: string;
  stage: string;
  percent: number;
  logs: string[];
  elapsed: number;
  warnings: string[];
  eta_seconds?: number;
}

// ── API Functions ──────────────────────────────────────────────────────

export function fetchJobs(limit = 20, offset = 0): Promise<JobsResponse> {
  return apiFetch<JobsResponse>(`/api/jobs?limit=${limit}&offset=${offset}`);
}

export function fetchJob(jobId: string): Promise<Job> {
  return apiFetch<Job>(`/api/jobs/${jobId}`);
}

export function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<UploadResponse>("/api/upload", {
    method: "POST",
    body: formData,
  });
}

export function startPipeline(
  jobId: string,
  formats: string[],
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/api/start", {
    method: "POST",
    body: JSON.stringify({ job_id: jobId, formats }),
  });
}

export function fetchProgress(jobId: string): Promise<ProgressData> {
  return apiFetch<ProgressData>(`/api/progress/${jobId}`);
}

export function cancelJob(jobId: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/cancel/${jobId}`, {
    method: "POST",
  });
}

/**
 * Build a download URL for a job artifact.
 * Returns a path string — caller handles the actual download (e.g. window.open).
 */
export function downloadUrl(jobId: string, fileType: string): string {
  return `/api/download/${jobId}/${fileType}`;
}
