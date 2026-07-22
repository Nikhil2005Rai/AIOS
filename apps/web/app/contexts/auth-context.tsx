"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";

export type UserType = {
  id: string;
  email: string;
  name: string;
  emailVerified: boolean;
  createdAt: string;
  updatedAt: string;
  image?: string | null;
  preferred_provider?: string | null;
};

type AuthContextType = {
  token: string | null;
  user: UserType | null;
  isLoaded: boolean;
  isSignedIn: boolean;
  isAuthenticated: boolean;
  mounted: boolean;
  sessionPending: boolean;
  getToken: () => Promise<string | null>;
  login: (token: string, user: UserType) => void;
  logout: () => void;
  refetchUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserType | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const fetchUser = useCallback(async (authToken: string) => {
    try {
      const res = await fetch(`${API_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
      } else {
        // Token expired or invalid
        localStorage.removeItem("aios_token");
        setToken(null);
        setUser(null);
      }
    } catch {
      // API down or network issue
    } finally {
      setIsLoaded(true);
    }
  }, []);

  useEffect(() => {
    const storedToken = typeof window !== "undefined" ? localStorage.getItem("aios_token") : null;
    if (storedToken) {
      setToken(storedToken);
      fetchUser(storedToken);
    } else {
      setIsLoaded(true);
    }
  }, [fetchUser]);

  const getToken = async (): Promise<string | null> => {
    return token || (typeof window !== "undefined" ? localStorage.getItem("aios_token") : null);
  };

  const login = (newToken: string, newUser: UserType) => {
    localStorage.setItem("aios_token", newToken);
    setToken(newToken);
    setUser(newUser);
    setIsLoaded(true);
  };

  const logout = () => {
    localStorage.removeItem("aios_token");
    setToken(null);
    setUser(null);
    router.push("/auth");
  };

  const refetchUser = async () => {
    const currentToken = token || localStorage.getItem("aios_token");
    if (currentToken) {
      await fetchUser(currentToken);
    }
  };

  const isSignedIn = !!token && !!user;
  const isAuthenticated = isSignedIn;

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isLoaded,
        isSignedIn,
        isAuthenticated,
        mounted: isLoaded,
        sessionPending: !isLoaded,
        getToken,
        login,
        logout,
        refetchUser,
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
