"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { authClient } from "../lib/auth-client";

export default function RootPage() {
  const router = useRouter();
  const { data: session, isPending } = authClient.useSession();

  useEffect(() => {
    if (!isPending) {
      if (session?.user) {
        router.replace("/chat");
      } else {
        router.replace("/auth");
      }
    }
  }, [isPending, session, router]);

  // Root page just redirects — show a brief loading state
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
