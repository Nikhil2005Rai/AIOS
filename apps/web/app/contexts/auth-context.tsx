"use client";

import React, { createContext, useContext, useState } from "react";
import { useRouter } from "next/navigation";
import { authClient } from "../../lib/auth-client";

type AuthContextType = {
  token: string | null;
  setToken: (token: string | null) => void;
  mounted: boolean;
  isAuthenticated: boolean;
  setIsAuthenticated: (v: boolean) => void;
  logout: () => void;
  // Better-Auth native session
  session: ReturnType<typeof authClient.useSession>["data"];
  sessionPending: boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  // Better-Auth's own session hook — fetches /api/auth/get-session automatically
  const { data: session, isPending: sessionPending } = authClient.useSession();

  // Derive auth state directly from Better-Auth session (no cookie parsing!)
  const isAuthenticated = !!session?.user;
  const token = session?.session?.token ?? null;

  // These setters are kept for backwards compatibility with existing callers
  // but they are no-ops now since session is managed by Better-Auth
  const setToken = (_token: string | null) => {};
  const setIsAuthenticated = (_v: boolean) => {};

  function logout() {
    authClient.signOut().then(() => {
      router.push("/auth");
    });
  }

  const mounted = !sessionPending;

  return (
    <AuthContext.Provider
      value={{
        token,
        setToken,
        mounted,
        isAuthenticated,
        setIsAuthenticated,
        logout,
        session,
        sessionPending,
      }}
    >
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
