"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AuthContextType = {
  token: string | null;
  setToken: (token: string | null) => void;
  mounted: boolean;
  isAuthenticated: boolean;
  setIsAuthenticated: (v: boolean) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    setMounted(true);

    const getSessionToken = () => {
      if (typeof document === "undefined") return null;
      const match = document.cookie.match(
        new RegExp("(^| )(?:__Secure-)?better-auth\\.session_token=([^;]+)")
      );
      return match ? match[2] : null;
    };

    const savedToken = getSessionToken();
    if (!savedToken) return;

    setToken(savedToken);

    // Verify token is valid before letting downstream contexts load data
    fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${savedToken}` },
    })
      .then((res) => {
        if (res.ok) {
          setIsAuthenticated(true);
        } else if (res.status === 401 || res.status === 403) {
          // Token is explicitly rejected by backend
          setToken(null);
          setIsAuthenticated(false);
        } else {
          // Backend returned non-auth status (e.g. 404/500/offline) — keep session
          setIsAuthenticated(true);
        }
      })
      .catch(() => {
        // Backend unreachable — keep session active on frontend
        setIsAuthenticated(true);
        console.warn("Auth check failed: backend may be offline");
      });
  }, []);

  function logout() {
    setToken(null);
    setIsAuthenticated(false);
    import("../../lib/auth-client").then(({ authClient }) => {
      authClient.signOut().then(() => {
        router.push("/");
      });
    });
  }

  return (
    <AuthContext.Provider value={{ token, setToken, mounted, isAuthenticated, setIsAuthenticated, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export { AuthContext };
