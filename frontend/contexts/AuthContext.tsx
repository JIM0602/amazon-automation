"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { clearTokens, setToken } from "@/lib/auth";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface User {
  username: string;
  role: "boss" | "operator";
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

// ── Context ────────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ── Provider ───────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  /**
   * Fetch current user info from /api/auth/me.
   * Called on mount to validate the stored token.
   */
  const fetchCurrentUser = useCallback(async () => {
    try {
      const me = await apiFetch<User>("/api/auth/me");
      setUser(me);
    } catch {
      // Token missing or invalid — user stays null
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Validate token on mount
  useEffect(() => {
    void fetchCurrentUser();
  }, [fetchCurrentUser]);

  /**
   * Authenticate with username/password.
   * Stores received tokens and fetches user profile.
   */
  const login = useCallback(
    async (username: string, password: string): Promise<void> => {
      const data = await apiFetch<LoginResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });

      setToken(data.access_token, data.refresh_token);

      const me = await apiFetch<User>("/api/auth/me");
      setUser(me);

      router.push("/dashboard");
    },
    [router]
  );

  /**
   * Clear tokens, reset state, and redirect to /login.
   */
  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    router.push("/login");
  }, [router]);

  const value: AuthContextValue = {
    user,
    loading,
    isAuthenticated: user !== null,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Hook ───────────────────────────────────────────────────────────────────────

/**
 * Hook to access auth context. Must be used inside AuthProvider.
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
