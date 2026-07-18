"use client";

import React from "react";
import { useChat } from "./chat-context";
import { useRouter } from "next/navigation";
import { LogOut, Lock, ArrowRight, Shield, Users } from "lucide-react";

export default function RootPage() {
  const router = useRouter();
  const {
    token,
    mounted,
    email,
    password,
    setEmail,
    setPassword,
    mode,
    setMode,
    status,
    statusIsError,
    handleAuth,
    logout,
  } = useChat();

  if (!mounted) return null;

  if (!token) {
    return (
      <main className="auth-shell">
        <form className="auth-panel" onSubmit={handleAuth}>
          <div className="brand-badge">A</div>
          <p className="eyebrow">Archimedes Portal</p>
          <h1>Access workspace</h1>
          <p className="auth-desc">Universal AI Enterprise Orchestration Workspace</p>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="user@example.com"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              minLength={mode === "register" ? 8 : 1}
              required
            />
          </label>
          <div className="auth-actions">
            <button type="submit">{mode === "login" ? "Login" : "Create account"}</button>
            <button type="button" className="ghost" onClick={() => setMode(mode === "login" ? "register" : "login")}>
              {mode === "login" ? "Create Account Instead" : "Sign In Instead"}
            </button>
          </div>
          {status !== "Ready" && status !== "Signed out" && (
            <p className={`status ${statusIsError ? "error" : ""}`} style={{ marginTop: 12 }}>{status}</p>
          )}
        </form>
      </main>
    );
  }

  // Authenticated: Render Workspace selection portal
  return (
    <main className="portal-shell">
      <div className="portal-container">
        <header className="portal-header">
          <div>
            <span style={{ fontSize: "0.8rem", textTransform: "uppercase", fontWeight: 700, color: "var(--accent)", letterSpacing: "0.05em" }}>Archimedes Platform</span>
            <h1>Orchestration Workspace</h1>
          </div>
          <div className="portal-user-section">
            <div className="portal-user-info">
              <span className="welcome">Authenticated User</span>
              <span className="username">{email ? email.split("@")[0] : "User"}</span>
            </div>
            <button
              type="button"
              className="ghost"
              onClick={logout}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "8px 12px",
                border: "2px solid #000000",
                borderRadius: 8,
                background: "#ffe4e6",
                color: "#e11d48",
                fontWeight: 700,
                cursor: "pointer",
                boxShadow: "2px 2px 0px 0px #000000"
              }}
            >
              <LogOut size={14} />
              <span>Logout</span>
            </button>
          </div>
        </header>

        <div className="portal-grid">
          {/* Card 1: Single User Workspace */}
          <div className="portal-card" onClick={() => router.push("/chat")}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ padding: 8, background: "#dbeafe", border: "2px solid #000000", borderRadius: 8, display: "flex", alignItems: "center" }}>
                <Shield size={24} style={{ color: "var(--accent)" }} />
              </div>
            </div>
            <h3>Single-User Workspace</h3>
            <p>
              Launch your private local instance of Archimedes. Fully featured LangGraph-based workflow automation, BYOK adapter settings, and custom document RAG indexes.
            </p>
            <button type="button" className="btn-portal" onClick={() => router.push("/chat")}>
              <span>Enter Workspace</span>
              <ArrowRight size={16} style={{ marginLeft: 8 }} />
            </button>
          </div>

          {/* Card 2: Collaborative Multi-User Workspace */}
          <div className="portal-card disabled">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ padding: 8, background: "#f1f5f9", border: "2px solid #cbd5e1", borderRadius: 8, display: "flex", alignItems: "center" }}>
                <Users size={24} style={{ color: "#94a3b8" }} />
              </div>
              <span className="badge-coming-soon">Coming Soon</span>
            </div>
            <h3>Collaborative Workspace</h3>
            <p>
              Coordinate with team members across shared chat threads, deploy co-owned RAG knowledge bases, and configure shared API adapter pools.
            </p>
            <button type="button" className="btn-portal" disabled>
              <Lock size={14} style={{ marginRight: 6 }} />
              <span>Locked</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
