"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { FormEvent } from "react";
import { createApiClient } from "../lib/api-client";
import { useAuth } from "./auth-context";

type ApiKeysContextType = {
  apiKeyProvider: "gemini" | "groq";
  setApiKeyProvider: (provider: "gemini" | "groq") => void;
  apiKeyValue: string;
  setApiKeyValue: (val: string) => void;
  apiKeyStatus: string;
  setApiKeyStatus: (status: string) => void;
  isSavingApiKey: boolean;
  configuredProviders: string[];
  preferredProvider: string | null;
  setPreferredProvider: (provider: string | null) => void;
  activeModelLabel: string;
  saveApiKey: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  deleteApiKey: (providerToDelete: "gemini" | "groq") => Promise<void>;
};

const ApiKeysContext = createContext<ApiKeysContextType | undefined>(undefined);

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const ApiKeysProvider = ({ children }: { children: React.ReactNode }) => {
  const { token, logout, isAuthenticated } = useAuth();

  const [apiKeyProvider, setApiKeyProvider] = useState<"gemini" | "groq">("gemini");
  const [apiKeyValue, setApiKeyValue] = useState("");
  const [apiKeyStatus, setApiKeyStatus] = useState("Configure your API keys");
  const [isSavingApiKey, setIsSavingApiKey] = useState(false);
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);
  const [preferredProvider, setPreferredProvider] = useState<string | null>(null);

  const activeModelLabel = (() => {
    if (preferredProvider === "gemini") return "Google Gemini (gemini-3.5-flash)";
    if (preferredProvider === "groq") return "Groq Client (llama-3.3-70b)";
    return "Default Model (gemini-3.5-flash)";
  })();

  useEffect(() => {
    if (!isAuthenticated || !token) return;

    // Load profile for preferred provider
    fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) {
          if (res.status === 401) { logout(); return null; }
          throw new Error("Profile request failed");
        }
        return res.json();
      })
      .then((data) => {
        if (data?.preferred_provider) {
          setPreferredProvider(data.preferred_provider);
        }
      })
      .catch((err) => console.error("Could not fetch user profile", err));

    // Load configured API keys
    fetch(`${API_URL}/users/me/api-keys`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) {
          if (res.status === 401) { logout(); return null; }
          throw new Error("API keys request failed");
        }
        return res.json();
      })
      .then((data) => {
        if (data?.providers) {
          const list = data.providers.map((p: any) => p.provider);
          setConfiguredProviders(list);
        }
      })
      .catch((err) => console.error("Could not fetch api keys", err));
  }, [isAuthenticated, token]);

  async function saveApiKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiKeyValue.trim()) {
      setApiKeyStatus("Enter a key before saving");
      return;
    }
    const api = createApiClient(token);
    setIsSavingApiKey(true);
    setApiKeyStatus("Saving key");
    try {
      const response = await api<{ provider: string; created_at: string }>("/users/me/api-keys", {
        method: "POST",
        body: JSON.stringify({ provider: apiKeyProvider, api_key: apiKeyValue.trim() }),
      });
      setApiKeyValue("");
      setApiKeyStatus(`${response.provider.toUpperCase()} API key saved successfully`);

      const nextProviders = [...new Set([...configuredProviders, apiKeyProvider])];
      setConfiguredProviders(nextProviders);
      setPreferredProvider(apiKeyProvider);
    } catch (error) {
      setApiKeyStatus(error instanceof Error ? error.message : "Could not save key");
    } finally {
      setIsSavingApiKey(false);
    }
  }

  async function deleteApiKey(providerToDelete: "gemini" | "groq") {
    const api = createApiClient(token);
    setIsSavingApiKey(true);
    setApiKeyStatus("Deleting key");
    try {
      await api(`/users/me/api-keys/${providerToDelete}`, { method: "DELETE" });
      setApiKeyStatus(`${providerToDelete.toUpperCase()} key deleted`);

      const nextProviders = configuredProviders.filter((p) => p !== providerToDelete);
      setConfiguredProviders(nextProviders);
      setPreferredProvider(nextProviders[0] ?? null);
    } catch (error) {
      setApiKeyStatus(error instanceof Error ? error.message : "Could not delete key");
    } finally {
      setIsSavingApiKey(false);
    }
  }

  return (
    <ApiKeysContext.Provider
      value={{
        apiKeyProvider,
        setApiKeyProvider,
        apiKeyValue,
        setApiKeyValue,
        apiKeyStatus,
        setApiKeyStatus,
        isSavingApiKey,
        configuredProviders,
        preferredProvider,
        setPreferredProvider,
        activeModelLabel,
        saveApiKey,
        deleteApiKey,
      }}
    >
      {children}
    </ApiKeysContext.Provider>
  );
};

export function useApiKeys() {
  const context = useContext(ApiKeysContext);
  if (context === undefined) {
    throw new Error("useApiKeys must be used within an ApiKeysProvider");
  }
  return context;
}

export { ApiKeysContext };
