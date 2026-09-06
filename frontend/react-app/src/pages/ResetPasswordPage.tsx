/**
 * Reset password page — set a new password using a one-time token from the
 * reset link (e.g. /reset-password?token=...).
 */

import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { resetPassword } from "@/api/auth";

function getErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === "object") {
    const body = (err as { body?: { error?: string; message?: string } }).body;
    if (body?.error) return body.error;
    if (body?.message) return body.message;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!token) {
      setError("This reset link is invalid or has expired.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await resetPassword(token, password);
      setMessage(res.message);
    } catch (err) {
      setError(getErrorMessage(err, "Unable to reset password"));
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
          <h2 className="mb-6 text-xl font-semibold">Reset Password</h2>

          {message ? (
            <div className="space-y-4">
              <p
                data-testid="reset-success"
                className="badge-success rounded-lg px-4 py-2.5 text-sm"
              >
                {message}
              </p>
              <Link
                to="/login"
                className="inline-block text-sm text-accent-blue hover:underline"
              >
                Go to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="password"
                  className="mb-1 block text-sm text-text-secondary"
                >
                  New Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-border-glass bg-bg-glass px-4 py-2.5 text-text-primary placeholder-text-muted transition focus:focus-ring focus:outline-none"
                  placeholder="Enter new password"
                />
              </div>

              <div>
                <label
                  htmlFor="confirm"
                  className="mb-1 block text-sm text-text-secondary"
                >
                  Confirm Password
                </label>
                <input
                  id="confirm"
                  type="password"
                  required
                  minLength={6}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className="w-full rounded-lg border border-border-glass bg-bg-glass px-4 py-2.5 text-text-primary placeholder-text-muted transition focus:focus-ring focus:outline-none"
                  placeholder="Confirm new password"
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
                {isLoading ? "Resetting..." : "Reset password"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
