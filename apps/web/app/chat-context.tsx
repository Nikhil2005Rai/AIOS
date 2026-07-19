"use client";

import React, { createContext, useContext, useState, useEffect, FormEvent, useMemo } from "react";
import { useRouter, usePathname } from "next/navigation";

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Message = {
  id: string;
  role: string;
  content: string;
  tool_name: string | null;
  created_at: string;
};

export type SuggestionCard = {
  title: string;
  desc: string;
  prompt: string;
};

export type DocumentBase = {
  id: string;
  title: string;
  chunk_count: number;
  created_at: string;
};

type ChatContextType = {
  token: string | null;
  setToken: (token: string | null) => void;
  mounted: boolean;
  conversations: Conversation[];
  setConversations: React.Dispatch<React.SetStateAction<Conversation[]>>;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  sidebarWidth: number;
  setSidebarWidth: (width: number) => void;
  isSidebarCollapsed: boolean;
  setIsSidebarCollapsed: (collapsed: boolean) => void;
  isSettingsOpen: boolean;
  setIsSettingsOpen: (open: boolean) => void;
  activeSettingsTab: "general" | "keys" | "knowledge";
  setActiveSettingsTab: (tab: "general" | "keys" | "knowledge") => void;
  draft: string;
  setDraft: (draft: string) => void;
  status: string;
  setStatus: (status: string) => void;
  isSending: boolean;
  apiKeyProvider: "gemini" | "groq";
  setApiKeyProvider: (provider: "gemini" | "groq") => void;
  apiKeyValue: string;
  setApiKeyValue: (val: string) => void;
  apiKeyStatus: string;
  setApiKeyStatus: (status: string) => void;
  isSavingApiKey: boolean;
  documentTitle: string;
  setDocumentTitle: (title: string) => void;
  documentContent: string;
  setDocumentContent: (content: string) => void;
  documentStatus: string;
  setDocumentStatus: (status: string) => void;
  isUploadingDocument: boolean;
  documents: DocumentBase[];
  configuredProviders: string[];
  preferredProvider: string | null;
  setPreferredProvider: (provider: string | null) => void;
  editingConversationId: string | null;
  setEditingConversationId: (id: string | null) => void;
  editingTitle: string;
  setEditingTitle: (title: string) => void;
  email: string;
  setEmail: (email: string) => void;
  password: string;
  setPassword: (password: string) => void;
  mode: "login" | "register";
  setMode: (mode: "login" | "register") => void;
  statusIsError: boolean;
  
  // Handlers
  api: <T>(endpoint: string, init?: RequestInit) => Promise<T>;
  handleAuth: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  loadDocuments: (authToken: string) => Promise<void>;
  deleteDocument: (docId: string) => Promise<void>;
  loadConversations: (authToken: string) => Promise<void>;
  loadMessages: (authToken: string, conversationId: string) => Promise<void>;
  createConversation: () => Promise<Conversation | null>;
  deleteConversation: (conversationId: string) => Promise<void>;
  renameConversation: (conversationId: string, newTitle: string) => Promise<void>;
  sendMessage: (event?: FormEvent<HTMLFormElement>, textOverride?: string, conversationIdOverride?: string) => Promise<void>;
  saveApiKey: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  deleteApiKey: (providerToDelete: "gemini" | "groq") => Promise<void>;
  uploadDocument: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  logout: () => void;
  
  // Helpers
  activeModelLabel: string;
  conversationGroups: [string, Conversation[]][];
  suggestionCards: SuggestionCard[];
};

const ChatContext = createContext<ChatContextType | undefined>(undefined);

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const suggestionCards: SuggestionCard[] = [
  {
    title: "Write design specs",
    desc: "Draft a system integration document",
    prompt: "Write a high-level system integration design specification for connecting FastAPI with next.js via REST, including error boundaries.",
  },
  {
    title: "Audit database indexes",
    desc: "Recommend indexing strategies for pgvector",
    prompt: "Provide an optimal indexing strategy for pgvector HNSW index configurations on high dimension vector models (e.g. 768 dimensions).",
  },
  {
    title: "Optimize API routes",
    desc: "Analyze dependencies and middleware latency",
    prompt: "Show how to structure modular FastAPI dependencies to reuse database connections, leverage NullPool correctly, and reduce connection overhead.",
  },
  {
    title: "Draft release notes",
    desc: "Summarize brutalist design system updates",
    prompt: "Draft comprehensive release notes explaining the resizable/collapsible retro-brutalist sidebar features, dynamic routes, and SVG icons.",
  },
];

export const ChatProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const pathname = usePathname();
  
  const [token, setToken] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("Ready");
  const [isSending, setIsSending] = useState(false);
  const [apiKeyProvider, setApiKeyProvider] = useState<"gemini" | "groq">("gemini");
  const [apiKeyValue, setApiKeyValue] = useState("");
  const [apiKeyStatus, setApiKeyStatus] = useState("Configure your API keys");
  const [isSavingApiKey, setIsSavingApiKey] = useState(false);
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentContent, setDocumentContent] = useState("");
  const [documentStatus, setDocumentStatus] = useState("No knowledge uploaded");
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [documents, setDocuments] = useState<DocumentBase[]>([]);
  
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);
  const [preferredProvider, setPreferredProvider] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [activeSettingsTab, setActiveSettingsTab] = useState<"general" | "keys" | "knowledge">("keys");
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  
  const statusIsError = useMemo(() => {
    const lower = status.toLowerCase();
    return lower.includes("failed") || lower.includes("error") || lower.includes("could not");
  }, [status]);

  const activeModelLabel = useMemo(() => {
    if (preferredProvider === "gemini") return "Google Gemini (gemini-3.5-flash)";
    if (preferredProvider === "groq") return "Groq Client (llama-3.3-70b)";
    return "Default Model (gemini-3.5-flash)";
  }, [preferredProvider]);

  const conversationGroups = useMemo(() => {
    const today: Conversation[] = [];
    const yesterday: Conversation[] = [];
    const older: Conversation[] = [];

    const now = new Date();
    const oneDay = 24 * 60 * 60 * 1000;

    conversations.forEach((c) => {
      const date = new Date(c.created_at);
      const diff = now.getTime() - date.getTime();
      if (diff < oneDay) {
        today.push(c);
      } else if (diff < 2 * oneDay) {
        yesterday.push(c);
      } else {
        older.push(c);
      }
    });

    const groups: [string, Conversation[]][] = [];
    if (today.length > 0) groups.push(["Today", today]);
    if (yesterday.length > 0) groups.push(["Yesterday", yesterday]);
    if (older.length > 0) groups.push(["Older", older]);
    return groups;
  }, [conversations]);

  useEffect(() => {
    setMounted(true);
    const savedToken = window.localStorage.getItem("ai-os-token");
    if (savedToken) {
      setToken(savedToken);
      
      // Load profile info
      fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${savedToken}` }
      })
      .then(res => {
        if (!res.ok) {
          if (res.status === 401) {
            logout();
            return null;
          }
          throw new Error("Profile request failed");
        }
        return res.json();
      })
      .then(dataMe => {
        if (dataMe) {
          if (dataMe.email) {
            setEmail(dataMe.email);
          }
          if (dataMe.preferred_provider) {
            setPreferredProvider(dataMe.preferred_provider);
          }
        }
      })
      .catch(err => console.error("Could not fetch user profile", err));

      // Load config API keys
      fetch(`${API_URL}/users/me/api-keys`, {
        headers: { Authorization: `Bearer ${savedToken}` }
      })
      .then(res => {
        if (!res.ok) {
          if (res.status === 401) {
            logout();
            return null;
          }
          throw new Error("API keys request failed");
        }
        return res.json();
      })
      .then(dataKeys => {
        if (dataKeys && dataKeys.providers) {
          const list = dataKeys.providers.map((p: any) => p.provider);
          setConfiguredProviders(list);
        }
      })
      .catch(err => console.error("Could not fetch api keys", err));

      void loadDocuments(savedToken);
    }
  }, []);

  useEffect(() => {
    if (token) {
      void loadConversations(token);
    }
  }, [token]);

  async function api<T>(endpoint: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data);
      throw new Error(detail || "Request failed");
    }
    return data as T;
  }

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Authenticating");
    try {
      const data = await api<{ access_token: string }>(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      window.localStorage.setItem("ai-os-token", data.access_token);
      setToken(data.access_token);
      setStatus("Signed in");

      fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` }
      })
      .then(res => {
        if (!res.ok) {
          if (res.status === 401) logout();
          throw new Error("Profile request failed");
        }
        return res.json();
      })
      .then(dataMe => {
        if (dataMe.email) {
          setEmail(dataMe.email);
        }
        if (dataMe.preferred_provider) {
          setPreferredProvider(dataMe.preferred_provider);
        }
      })
      .catch(err => console.error("Could not fetch user profile on login", err));

      fetch(`${API_URL}/users/me/api-keys`, {
        headers: { Authorization: `Bearer ${data.access_token}` }
      })
      .then(res => {
        if (!res.ok) {
          if (res.status === 401) logout();
          throw new Error("API keys request failed");
        }
        return res.json();
      })
      .then(dataKeys => {
        if (dataKeys.providers) {
          const list = dataKeys.providers.map((p: any) => p.provider);
          setConfiguredProviders(list);
        }
      })
      .catch(err => console.error("Could not fetch api keys on login", err));

      void loadDocuments(data.access_token);
      router.push("/"); // Direct to select workspace screen
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Authentication failed");
    }
  }

  async function loadDocuments(authToken: string) {
    try {
      const response = await fetch(`${API_URL}/documents`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      }
    } catch (error) {
      console.error("Could not load documents", error);
    }
  }

  async function deleteDocument(docId: string) {
    try {
      await api(`/documents/${docId}`, {
        method: "DELETE",
      });
      setDocuments((current) => current.filter((doc) => doc.id !== docId));
    } catch (error) {
      console.error("Could not delete document", error);
    }
  }

  async function loadConversations(authToken: string) {
    setStatus("Loading conversations");
    try {
      const response = await fetch(`${API_URL}/conversations`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const data = (await response.json()) as Conversation[];
      if (!response.ok) {
        throw new Error("Could not load conversations");
      }
      setConversations(data);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load conversations");
    }
  }

  async function loadMessages(authToken: string, conversationId: string) {
    try {
      const response = await fetch(`${API_URL}/conversations/${conversationId}/messages`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const data = (await response.json()) as Message[];
      if (!response.ok) {
        throw new Error("Could not load messages");
      }
      setMessages(data);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load messages");
    }
  }

  async function createConversation(): Promise<Conversation | null> {
    setStatus("Creating conversation");
    try {
      const conversation = await api<Conversation>("/conversations", {
        method: "POST",
        body: JSON.stringify({ title: `New session ${conversations.length + 1}` }),
      });
      setConversations((current) => [conversation, ...current]);
      setMessages([]);
      setStatus("Ready");
      router.push(`/chat/${conversation.id}`);
      return conversation;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create conversation");
      return null;
    }
  }

  async function deleteConversation(conversationId: string) {
    setStatus("Deleting conversation");
    try {
      await api(`/conversations/${conversationId}`, {
        method: "DELETE",
      });
      const remaining = conversations.filter((c) => c.id !== conversationId);
      setConversations(remaining);
      if (activeConversationId === conversationId) {
        setMessages([]);
        router.push("/chat");
      }
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not delete conversation");
    }
  }

  async function renameConversation(conversationId: string, newTitle: string) {
    if (!newTitle.trim()) return;
    setStatus("Renaming");
    try {
      await api(`/conversations/${conversationId}`, {
        method: "PUT",
        body: JSON.stringify({ title: newTitle.trim() }),
      });
      setConversations((current) =>
        current.map((c) => (c.id === conversationId ? { ...c, title: newTitle.trim() } : c))
      );
      setEditingConversationId(null);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not rename conversation");
    }
  }

  async function sendMessage(event?: FormEvent<HTMLFormElement>, textOverride?: string, conversationIdOverride?: string) {
    if (event) event.preventDefault();
    const content = textOverride ?? draft.trim();
    const targetId = conversationIdOverride ?? activeConversationId;
    if (!targetId || !content) return;

    setIsSending(true);
    setDraft("");
    setStatus("Planner is working");

    try {
      const response = await api<{ job_id: string; status: string; user_message: Message }>(
        `/conversations/${targetId}/messages`,
        { method: "POST", body: JSON.stringify({ content }) },
      );

      if (targetId === activeConversationId || (!activeConversationId && targetId)) {
        setMessages((current) => [...current, response.user_message]);
      }

      const jobId = response.job_id;
      const startTime = Date.now();
      const timeoutMs = 60000; // 60 seconds

      const poll = async () => {
        if (Date.now() - startTime > timeoutMs) {
          setStatus("Planner timed out after 60 seconds");
          setIsSending(false);
          return;
        }
        try {
          const job = await api<{
            job_id: string;
            status: string;
            assistant_message: Message | null;
            error: string | null;
          }>(`/conversations/${targetId}/messages/jobs/${jobId}`);

          if (job.status === "succeeded" && job.assistant_message) {
            if (targetId === activeConversationId) {
              setMessages((current) => [...current, job.assistant_message as Message]);
            }
            setStatus(job.assistant_message.tool_name ? `Used ${job.assistant_message.tool_name}` : "Ready");
            setIsSending(false);
            void loadConversations(token as string);
          } else if (job.status === "failed") {
            const message = job.error ?? "Planner failed";
            setStatus(message);
            if (targetId === activeConversationId) {
              setMessages((current) => [
                ...current,
                {
                  id: `local-error-${Date.now()}`,
                  role: "assistant",
                  content: `Request failed: ${message}`,
                  tool_name: null,
                  created_at: new Date().toISOString(),
                },
              ]);
            }
            setIsSending(false);
          } else {
            setTimeout(poll, 1000);
          }
        } catch (pollError) {
          setStatus(pollError instanceof Error ? pollError.message : "Polling failed");
          setIsSending(false);
        }
      };

      setTimeout(poll, 1000);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Planner failed";
      setStatus(message);
      setMessages((current) => [
        ...current,
        {
          id: `local-error-${Date.now()}`,
          role: "assistant",
          content: `Request failed: ${message}`,
          tool_name: null,
          created_at: new Date().toISOString(),
        },
      ]);
      setIsSending(false);
    }
  }

  async function saveApiKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiKeyValue.trim()) {
      setApiKeyStatus("Enter a key before saving");
      return;
    }
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
    setIsSavingApiKey(true);
    setApiKeyStatus("Deleting key");
    try {
      await api(`/users/me/api-keys/${providerToDelete}`, {
        method: "DELETE",
      });
      setApiKeyStatus(`${providerToDelete.toUpperCase()} key deleted`);
      
      const nextProviders = configuredProviders.filter(p => p !== providerToDelete);
      setConfiguredProviders(nextProviders);
      setPreferredProvider(nextProviders[0] ?? null);
    } catch (error) {
      setApiKeyStatus(error instanceof Error ? error.message : "Could not delete key");
    } finally {
      setIsSavingApiKey(false);
    }
  }

  async function uploadDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!documentTitle.trim() || !documentContent.trim()) {
      setDocumentStatus("Add a title and content");
      return;
    }
    setIsUploadingDocument(true);
    setDocumentStatus("Queued");
    
    try {
      const response = await api<{ job_id: string; status: string }>("/documents", {
        method: "POST",
        body: JSON.stringify({ title: documentTitle.trim(), content: documentContent.trim() }),
      });
      
      const jobId = response.job_id;
      const startTime = Date.now();
      const timeoutMs = 120000; // 2 minutes
      
      const poll = async () => {
        if (Date.now() - startTime > timeoutMs) {
          setDocumentStatus("Ingestion timed out after 2 minutes");
          setIsUploadingDocument(false);
          return;
        }
        
        try {
          const job = await api<{
            job_id: string;
            status: string;
            result: { title: string; chunk_count: number } | null;
            error: string | null;
          }>(`/documents/jobs/${jobId}`);
          
          if (job.status === "queued") {
            setDocumentStatus("Queued");
            setTimeout(poll, 1500);
          } else if (job.status === "running") {
            setDocumentStatus("Embedding knowledge");
            setTimeout(poll, 1500);
          } else if (job.status === "succeeded") {
            const res = job.result;
            setDocumentTitle("");
            setDocumentContent("");
            setDocumentStatus(`${res?.title ?? "Document"} saved (${res?.chunk_count ?? 0} chunks)`);
            setIsUploadingDocument(false);
            void loadDocuments(token as string);
          } else if (job.status === "failed") {
            setDocumentStatus(`Ingestion failed: ${job.error ?? "Unknown error"}`);
            setIsUploadingDocument(false);
          } else {
            setTimeout(poll, 1500);
          }
        } catch (pollError) {
          setDocumentStatus(pollError instanceof Error ? pollError.message : "Polling failed");
          setIsUploadingDocument(false);
        }
      };
      
      setTimeout(poll, 1500);
      
    } catch (error) {
      setDocumentStatus(error instanceof Error ? error.message : "Could not upload knowledge");
      setIsUploadingDocument(false);
    }
  }

  function logout() {
    window.localStorage.removeItem("ai-os-token");
    setToken(null);
    setConversations([]);
    setMessages([]);
    setEmail("");
    setPassword("");
    router.push("/");
  }

  return (
    <ChatContext.Provider
      value={{
        token,
        setToken,
        mounted,
        conversations,
        setConversations,
        activeConversationId,
        setActiveConversationId,
        messages,
        setMessages,
        sidebarWidth,
        setSidebarWidth,
        isSidebarCollapsed,
        setIsSidebarCollapsed,
        isSettingsOpen,
        setIsSettingsOpen,
        activeSettingsTab,
        setActiveSettingsTab,
        draft,
        setDraft,
        status,
        setStatus,
        isSending,
        apiKeyProvider,
        setApiKeyProvider,
        apiKeyValue,
        setApiKeyValue,
        apiKeyStatus,
        setApiKeyStatus,
        isSavingApiKey,
        documentTitle,
        setDocumentTitle,
        documentContent,
        setDocumentContent,
        documentStatus,
        setDocumentStatus,
        isUploadingDocument,
        documents,
        configuredProviders,
        preferredProvider,
        setPreferredProvider,
        editingConversationId,
        setEditingConversationId,
        editingTitle,
        setEditingTitle,
        email,
        setEmail,
        password,
        setPassword,
        mode,
        setMode,
        statusIsError,
        
        // Handlers
        api,
        handleAuth,
        loadDocuments,
        deleteDocument,
        loadConversations,
        loadMessages,
        createConversation,
        deleteConversation,
        renameConversation,
        sendMessage,
        saveApiKey,
        deleteApiKey,
        uploadDocument,
        logout,
        
        // Helpers
        activeModelLabel,
        conversationGroups,
        suggestionCards,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};
