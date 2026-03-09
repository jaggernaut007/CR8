/**
 * Top navigation bar with glassmorphism styling.
 */

import { Link, useNavigate } from "react-router";
import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  if (!user) return null;

  return (
    <nav className="glass border-b border-border-glass px-6 py-3">
      <div className="mx-auto flex max-w-6xl items-center justify-between">
        <Link to="/dashboard" className="text-lg font-bold">
          <span className="accent-gradient bg-clip-text text-transparent">
            CR8
          </span>
        </Link>

        <div className="flex items-center gap-4">
          <span className="text-sm text-text-secondary">
            {user.display_name || user.email}
          </span>
          <button
            onClick={handleLogout}
            className="rounded-lg border border-border-glass px-3 py-1.5 text-sm text-text-secondary transition hover:bg-bg-glass-hover"
          >
            Sign Out
          </button>
        </div>
      </div>
    </nav>
  );
}
