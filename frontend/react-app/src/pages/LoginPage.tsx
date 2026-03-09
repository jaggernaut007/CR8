/**
 * Login / Register page with glassmorphism card.
 *
 * Features:
 * - Toggle between Sign In and Create Account modes
 * - "How it works" section with 3 steps (Upload, Generate, Learn)
 * - Error display with auto-clear
 * - Loading spinner during auth requests
 */

import { useState, useEffect, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const { user, login, register, error, clearError, isLoading } = useAuth();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (user && !isLoading) {
      navigate("/dashboard", { replace: true });
    }
  }, [user, isLoading, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      if (isRegister) {
        await register(email, password, displayName || undefined);
      } else {
        await login(email, password);
      }
      navigate("/dashboard");
    } catch {
      // Error is set in AuthContext
    }
  };

  const toggleMode = () => {
    setIsRegister((prev) => !prev);
    clearError();
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo / Title */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight">
            <span className="accent-gradient bg-clip-text text-transparent">
              CR8
            </span>
          </h1>
          <p className="mt-2 text-text-secondary">
            Adaptive Learning Pipeline
          </p>
        </div>

        {/* Auth Card */}
        <div className="glass glass-shadow p-8">
          <h2 className="mb-6 text-xl font-semibold">
            {isRegister ? "Create Account" : "Sign In"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label
                  htmlFor="displayName"
                  className="mb-1 block text-sm text-text-secondary"
                >
                  Display Name
                </label>
                <input
                  id="displayName"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full rounded-lg border border-border-glass bg-bg-glass px-4 py-2.5 text-text-primary placeholder-text-muted transition focus:focus-ring focus:outline-none"
                  placeholder="Your name"
                />
              </div>
            )}

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

            <div>
              <label
                htmlFor="password"
                className="mb-1 block text-sm text-text-secondary"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-border-glass bg-bg-glass px-4 py-2.5 text-text-primary placeholder-text-muted transition focus:focus-ring focus:outline-none"
                placeholder="Enter password"
              />
            </div>

            {error && (
              <div data-testid="auth-error" className="badge-error rounded-lg px-4 py-2.5 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="accent-gradient w-full rounded-lg px-4 py-2.5 font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading
                ? "Loading..."
                : isRegister
                  ? "Create Account"
                  : "Sign In"}
            </button>
          </form>

          <div className="mt-4 text-center text-sm text-text-secondary">
            {isRegister ? "Already have an account?" : "Need an account?"}{" "}
            <button
              onClick={toggleMode}
              className="text-accent-blue hover:underline"
            >
              {isRegister ? "Sign In" : "Create Account"}
            </button>
          </div>
        </div>

        {/* How it works */}
        <div className="mt-8 glass p-6">
          <h3 className="mb-4 text-center text-sm font-semibold uppercase tracking-wider text-text-secondary">
            How it works
          </h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <Step number="1" title="Upload" desc="Drop your curriculum PDF" />
            <Step number="2" title="Generate" desc="AI creates learning materials" />
            <Step number="3" title="Learn" desc="Interactive content & quizzes" />
          </div>
        </div>
      </div>
    </div>
  );
}

function Step({ number, title, desc }: { number: string; title: string; desc: string }) {
  return (
    <div>
      <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full accent-gradient text-sm font-bold text-white">
        {number}
      </div>
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <p className="mt-1 text-xs text-text-muted">{desc}</p>
    </div>
  );
}
