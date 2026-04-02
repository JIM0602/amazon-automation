"use client";

import { useAuth } from "@/contexts/AuthContext";

/**
 * Fixed top navigation bar.
 * Shows branding on the left, user info + logout on the right.
 */
export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-gray-900 border-b border-gray-700 flex items-center justify-between px-6">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <span className="text-xl font-bold text-white tracking-wide">
          PUDIWIND AI
        </span>
        <span className="text-gray-400 text-sm hidden sm:inline">
          管理控制台
        </span>
      </div>

      {/* User actions */}
      <div className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-gray-300 text-sm">
              {user.username}
              {user.role === "boss" && (
                <span className="ml-2 text-xs bg-amber-500 text-black px-1.5 py-0.5 rounded font-medium">
                  管理员
                </span>
              )}
            </span>
            <button
              onClick={logout}
              className="text-sm text-gray-400 hover:text-white transition-colors px-3 py-1.5 rounded border border-gray-600 hover:border-gray-400"
            >
              退出
            </button>
          </>
        )}
      </div>
    </header>
  );
}
