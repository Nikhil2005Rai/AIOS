"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AuthContextType = {
  token: string | null;
  setToken: (token: string | null) => void;
  mounted: boolean;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    const getSessionToken = () => {
      if (typeof document === "undefined") return null;
      const match = document.cookie.match(
        new RegExp("(^| )better-auth\\.session_token=([^;]+)")
      );
      return match ? match[2] : null;
    };

    const savedToken = getSessionToken();
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  function logout() {
    setToken(null);
    import("../../lib/auth-client").then(({ authClient }) => {
      authClient.signOut().then(() => {
        router.push("/");
      });
    });
  }

  return (
    <AuthContext.Provider value={{ token, setToken, mounted, logout }}>
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
