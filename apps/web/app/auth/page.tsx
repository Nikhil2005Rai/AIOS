"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { authClient } from "../../lib/auth-client";

export default function AuthPage() {
  const router = useRouter();
  const { data: session, isPending } = authClient.useSession();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // If user is already logged in, redirect to workspace
  useEffect(() => {
    if (!isPending && session?.user) {
      router.replace("/chat");
    }
  }, [session, isPending, router]);

  // Show nothing while checking session or if already authenticated
  if (isPending || session?.user) {
    return (
      <main className="auth-shell" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "var(--text-muted)", fontSize: "14px" }}>Loading...</div>
      </main>
    );
  }

  async function handleAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Authenticating...");
    setIsLoading(true);

    try {
      if (mode === "login") {
        const { error } = await authClient.signIn.email({ email, password });
        if (error) {
          setStatus(error.message || "Failed to login");
        } else {
          router.replace("/chat");
        }
      } else {
        const { error } = await authClient.signUp.email({
          email,
          password,
          name: email.split("@")[0],
        });
        if (error) {
          setStatus(error.message || "Failed to create account");
        } else {
          router.replace("/chat");
        }
      }
    } catch (err: any) {
      setStatus(err.message || "Failed to authenticate");
    } finally {
      setIsLoading(false);
    }
  }

  async function signInWithProvider(provider: "google" | "github") {
    setStatus(`Redirecting to ${provider}...`);
    try {
      await authClient.signIn.social({
        provider,
        callbackURL: window.location.origin + "/chat",
      });
    } catch (err: any) {
      setStatus(err?.message || `Failed to start ${provider} authentication`);
    }
  }

  return (
    <main className="auth-shell">
      <div className="auth-split-container">
        {/* Left Form Side */}
        <div className="auth-form-side">
          <div className="auth-form-header">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ width: 28, height: 28 }}
            >
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            Archimedes
          </div>

          <div className="auth-header-text">
            <h1>{mode === "login" ? "Welcome Back" : "Create an Account"}</h1>
            <p className="auth-desc">
              {mode === "login"
                ? "Enter your credentials to access your workspace."
                : "Sign up to start configuring AI OS agents and workflows."}
            </p>
          </div>

          <form
            onSubmit={handleAuth}
            style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "16px" }}
          >
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@company.com"
                required
              />
            </label>

            <label>
              Password
              <div style={{ position: "relative", width: "100%" }}>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  minLength={mode === "register" ? 8 : 1}
                  required
                  style={{ paddingRight: "40px", width: "100%" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: "absolute",
                    right: "10px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: "#64748b",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "4px",
                  }}
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>

            <div className="auth-options">
              <label style={{ display: "flex", gap: "8px" }}>
                <input
                  type="checkbox"
                  style={{ accentColor: "var(--accent)", width: "16px", height: "16px" }}
                />
                Remember Me
              </label>
              <a href="#">Forgot Your Password?</a>
            </div>

            <button type="submit" className="btn-primary-auth" disabled={isLoading}>
              {isLoading
                ? "Please wait..."
                : mode === "login"
                ? "Log In"
                : "Create Account"}
            </button>

            {status && (
              <p
                className={`status ${
                  status.includes("Fail") || status.includes("error") ? "error" : ""
                }`}
                style={{ textAlign: "center", margin: 0 }}
              >
                {status}
              </p>
            )}

            <div className="auth-divider">Or Continue With</div>

            <div className="social-btns-row">
              <button
                type="button"
                className="social-btn"
                onClick={() => signInWithProvider("google")}
              >
                <svg viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Google
              </button>

              <button
                type="button"
                className="social-btn"
                onClick={() => signInWithProvider("github")}
              >
                <svg viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
                  />
                </svg>
                GitHub
              </button>
            </div>
          </form>

          <p className="auth-footer-text">
            {mode === "login" ? "Don't Have An Account? " : "Already Have An Account? "}
            <a
              style={{ cursor: "pointer" }}
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setStatus("");
              }}
            >
              {mode === "login" ? "Register Now." : "Login Now."}
            </a>
          </p>

          <div className="auth-bottom-links">
            <span>Copyright © 2026 Archimedes Enterprises LTD.</span>
            <a href="#" style={{ color: "inherit", textDecoration: "none" }}>
              Privacy Policy
            </a>
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
              Log in to access your orchestrator dashboard, knowledge graphs, and deploy LLM
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
