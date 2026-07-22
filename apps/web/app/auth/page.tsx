"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../contexts/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function AuthPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn, login } = useAuth();

  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace("/chat");
    }
  }, [isLoaded, isSignedIn, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const endpoint = isSignUp ? "/auth/register" : "/auth/login";
    const body = isSignUp ? { email, password, name } : { email, password };

    try {
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Authentication failed");
      }

      login(data.access_token, data.user);
      router.push("/chat");
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  if (!isLoaded) {
    return (
      <main className="auth-shell" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "var(--text-muted)", fontSize: "14px" }}>Loading authentication...</div>
      </main>
    );
  }

  return (
    <main className="auth-shell">
      <div className="auth-split-container">
        {/* Left Form Side */}
        <div className="auth-form-side" style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "40px 24px" }}>
          <div className="auth-form-header" style={{ marginBottom: "24px", display: "flex", alignItems: "center", gap: "8px", fontSize: "24px", fontWeight: "700" }}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ width: 28, height: 28, color: "var(--accent, #6366f1)" }}
            >
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            Archimedes
          </div>

          <div style={{ width: "100%", maxWidth: "380px" }}>
            <div style={{ textAlign: "center", marginBottom: "24px" }}>
              <h1 style={{ fontSize: "20px", fontWeight: "600", marginBottom: "6px" }}>
                {isSignUp ? "Create an Account" : "Welcome Back"}
              </h1>
              <p style={{ fontSize: "14px", color: "#64748b" }}>
                {isSignUp ? "Sign up to start using Archimedes AI-OS" : "Sign in to access your workspace"}
              </p>
            </div>

            {error && (
              <div style={{ padding: "10px 14px", marginBottom: "16px", borderRadius: "8px", background: "#fef2f2", color: "#dc2626", fontSize: "13px", border: "1px solid #fecaca" }}>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {isSignUp && (
                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: "500", marginBottom: "6px" }}>
                    Full Name
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Jane Doe"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      borderRadius: "8px",
                      border: "1px solid #cbd5e1",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                </div>
              )}

              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: "500", marginBottom: "6px" }}>
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  placeholder="user@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "8px",
                    border: "1px solid #cbd5e1",
                    fontSize: "14px",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: "500", marginBottom: "6px" }}>
                  Password
                </label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "8px",
                    border: "1px solid #cbd5e1",
                    fontSize: "14px",
                    outline: "none",
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "12px",
                  borderRadius: "8px",
                  background: "var(--accent, #6366f1)",
                  color: "#ffffff",
                  fontSize: "14px",
                  fontWeight: "600",
                  border: "none",
                  cursor: loading ? "not-allowed" : "pointer",
                  opacity: loading ? 0.7 : 1,
                  marginTop: "8px",
                }}
              >
                {loading ? "Processing..." : isSignUp ? "Sign Up" : "Sign In"}
              </button>
            </form>

            <div style={{ textAlign: "center", marginTop: "20px", fontSize: "13px", color: "#64748b" }}>
              {isSignUp ? "Already have an account?" : "Don't have an account?"}{" "}
              <button
                type="button"
                onClick={() => {
                  setIsSignUp(!isSignUp);
                  setError(null);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--accent, #6366f1)",
                  fontWeight: "600",
                  cursor: "pointer",
                  padding: 0,
                  textDecoration: "underline",
                }}
              >
                {isSignUp ? "Sign In" : "Sign Up"}
              </button>
            </div>
          </div>

          <div className="auth-bottom-links" style={{ marginTop: "32px", fontSize: "12px", color: "#94a3b8" }}>
            <span>Copyright © 2026 Archimedes Enterprises LTD.</span>
          </div>
        </div>

        {/* Right Graphic Side */}
        <div className="auth-graphic-side">
          <div className="bg-shape bg-shape-1"></div>
          <div className="bg-shape bg-shape-2"></div>

          <div className="auth-graphic-text">
            <h2>
              Effortlessly manage your
              <br />
              agents and operations.
            </h2>
            <p>
              Sign in to access your orchestrator dashboard, knowledge graphs, and deploy LLM
              configurations.
            </p>
          </div>

          <div className="auth-graphic-dashboard">
            <svg viewBox="0 0 400 300" className="dashboard-svg" xmlns="http://www.w3.org/2000/svg">
              <rect x="20" y="20" width="360" height="260" rx="16" fill="#ffffff" className="svg-float-1" />
              <rect x="40" y="40" width="120" height="12" rx="6" fill="#e2e8f0" className="svg-float-1" />
              <rect x="40" y="60" width="80" height="8" rx="4" fill="#cbd5e1" className="svg-float-1" />

              <g transform="translate(40, 90)" className="svg-float-2">
                <rect width="140" height="100" rx="12" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="2" />
                <path d="M 20 80 Q 40 40, 70 60 T 120 20" fill="none" stroke="var(--accent)" strokeWidth="4" strokeLinecap="round" />
                <circle cx="20" cy="80" r="4" fill="var(--accent)" />
                <circle cx="70" cy="60" r="4" fill="var(--accent)" />
                <circle cx="120" cy="20" r="4" fill="var(--accent)" />
              </g>

              <g transform="translate(200, 90)" className="svg-float-3">
                <rect width="140" height="150" rx="12" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="2" />
                <circle cx="70" cy="70" r="40" fill="none" stroke="#e2e8f0" strokeWidth="16" />
                <circle cx="70" cy="70" r="40" fill="none" stroke="var(--accent)" strokeWidth="16" strokeDasharray="180 1000" strokeLinecap="round" transform="rotate(-90 70 70)" className="svg-ring" />
                <text x="70" y="76" textAnchor="middle" fontSize="16" fontWeight="bold" fill="var(--text)">92%</text>
                <rect x="20" y="130" width="100" height="6" rx="3" fill="#e2e8f0" />
              </g>

              <g transform="translate(40, 205)" className="svg-float-2">
                <rect x="0" y="0" width="140" height="45" rx="8" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="2" />
                <rect x="15" y="15" width="20" height="20" rx="4" fill="var(--accent)" className="svg-bar" />
                <rect x="45" y="10" width="20" height="25" rx="4" fill="#6366f1" className="svg-bar" style={{ animationDelay: "0.2s" }} />
                <rect x="75" y="20" width="20" height="15" rx="4" fill="#818cf8" className="svg-bar" style={{ animationDelay: "0.4s" }} />
                <rect x="105" y="5" width="20" height="30" rx="4" fill="#c7d2fe" className="svg-bar" style={{ animationDelay: "0.6s" }} />
              </g>
            </svg>
          </div>
        </div>
      </div>
    </main>
  );
}
