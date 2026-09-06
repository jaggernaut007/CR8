/**
 * Forgot password page — request a password reset link by email.
 */

import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { requestPasswordReset } from "@/api/auth";

function getErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === "object") {
    const body = (err as { body?: { error?: string; message?: string } }).body;
    if (body?.error) return body.error;
    if (body?.message) return body.message;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setIsLoading(true);
    try {
      const res = await requestPasswordReset(email);
      setMessage(res.message);
      setEmail("");
    } catch (err) {
      setError(getErrorMessage(err, "Unable to send reset email"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight">
            <span className="accent-gradient bg-clip-text text-transparent">
              CR8
            </span>
          </h1>
          <p className="mt-2 text-text-secondary">Adaptive Learning Pipeline</p>
        </div>

        <div className="glass glass-shadow p-8">
          <h2 className="mb-6 text-xl font-semibold">Forgot Password</h2>

          {message ? (
            <div className="space-y-4">
              <p
                data-testid="forgot-success"
                className="badge-success rounded-lg px-4 py-2.5 text-sm"
              >
                {message}
              </p>
              <Link
                to="/login"
                className="inline-block text-sm text-accent-blue hover:underline"
              >
                Back to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <p className="text-sm text-text-secondary">
                Enter your email and we&apos;ll send you a link to reset your
                password.
              </p>

              <div>
                <label
                  htmlFor="email"
                  className="mb-1 block text-sm text-text-secondary"
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-border-glass bg-bg-glass px-4 py-2.5 text-text-primary placeholder-text-muted transition focus:focus-ring focus:outline-none"
                  placeholder="you@university.edu"
                />
              </div>

              {error && (
                <div
                  data-testid="auth-error"
                  className="badge-error rounded-lg px-4 py-2.5 text-sm"
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="accent-gradient w-full rounded-lg px-4 py-2.5 font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLoading ? "Sending..." : "Send reset link"}
              </button>

              <div className="text-center text-sm text-text-secondary">
                <Link
                  to="/login"
                  className="text-accent-blue hover:underline"
                >
                  Back to sign in
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
