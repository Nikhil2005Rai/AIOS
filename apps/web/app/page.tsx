"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./contexts/auth-context";

export default function RootPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (isLoaded) {
      if (isSignedIn) {
        router.replace("/chat");
      } else {
        router.replace("/auth");
      }
    }
  }, [isLoaded, isSignedIn, router]);

  return (
    <main style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      background: "var(--background, #0f172a)",
      color: "var(--text-muted, #64748b)",
      fontSize: "14px"
    }}>
      Loading...
    </main>
  );
}
