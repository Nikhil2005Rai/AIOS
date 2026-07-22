"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  FormEvent,
  useMemo,
} from "react";
import { useRouter } from "next/navigation";
import { createApiClient } from "../lib/api-client";
import { useAuth } from "./auth-context";
import { useUi } from "./ui-context";
import { useApiKeys } from "./api-keys-context";
import { pollJob } from "../hooks/use-job-poller";
import toast from "react-hot-toast";

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

export const suggestionCards: SuggestionCard[] = [
  {
    title: "Write design specs",
    desc: "Draft a system integration document",
    prompt:
      "Write a high-level system integration design specification for connecting FastAPI with next.js via REST, including error boundaries.",
  },
  {
    title: "Audit database indexes",
    desc: "Recommend indexing strategies for pgvector",
    prompt:
      "Provide an optimal indexing strategy for pgvector HNSW index configurations on high dimension vector models (e.g. 768 dimensions).",
  },
  {
    title: "Optimize API routes",
    desc: "Analyze dependencies and middleware latency",
    prompt:
      "Show how to structure modular FastAPI dependencies to reuse database connections, leverage NullPool correctly, and reduce connection overhead.",
  },
  {
    title: "Draft release notes",
    desc: "Summarize brutalist design system updates",
    prompt:
      "Draft comprehensive release notes explaining the resizable/collapsible retro-brutalist sidebar features, dynamic routes, and SVG icons.",
  },
];

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ConversationContextType = {
  conversations: Conversation[];
  setConversations: React.Dispatch<React.SetStateAction<Conversation[]>>;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  editingConversationId: string | null;
  setEditingConversationId: (id: string | null) => void;
  editingTitle: string;
  setEditingTitle: (title: string) => void;
  conversationGroups: [string, Conversation[]][];
  loadConversations: (authToken?: string) => Promise<void>;
  loadMessages: (authToken: string | undefined, conversationId: string) => Promise<void>;
  createConversation: () => Promise<Conversation | null>;
  deleteConversation: (conversationId: string) => Promise<void>;
  renameConversation: (conversationId: string, newTitle: string) => Promise<void>;
  sendMessage: (
    event?: FormEvent<HTMLFormElement>,
    textOverride?: string,
    conversationIdOverride?: string
  ) => Promise<void>;
};

const ConversationContext = createContext<ConversationContextType | undefined>(undefined);

export const ConversationProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const { getToken, isAuthenticated } = useAuth();
  const { setStatus, setIsSending, setDraft, draft, setIsApiKeyWarningOpen } = useUi();
  const { configuredProviders } = useApiKeys();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  useEffect(() => {
    if (isAuthenticated) {
      void loadConversations();
    }
  }, [isAuthenticated]);

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

  async function loadConversations(authToken?: string) {
    setStatus("Loading conversations");
    try {
      const bearerToken = authToken ?? (await getToken());
      if (!bearerToken) return;
      const response = await fetch(`${API_URL}/conversations`, {
        headers: { Authorization: `Bearer ${bearerToken}` },
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

  async function loadMessages(authToken: string | undefined, conversationId: string) {
    try {
      const bearerToken = authToken ?? (await getToken());
      if (!bearerToken) return;
      const response = await fetch(
        `${API_URL}/conversations/${conversationId}/messages`,
        { headers: { Authorization: `Bearer ${bearerToken}` } }
      );
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
    const api = createApiClient(getToken);
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
    const api = createApiClient(getToken);
    setStatus("Deleting conversation");
    try {
      await api(`/conversations/${conversationId}`, { method: "DELETE" });
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
    const api = createApiClient(getToken);
    setStatus("Renaming");
    try {
      await api(`/conversations/${conversationId}`, {
        method: "PUT",
        body: JSON.stringify({ title: newTitle.trim() }),
      });
      setConversations((current) =>
        current.map((c) =>
          c.id === conversationId ? { ...c, title: newTitle.trim() } : c
        )
      );
      setEditingConversationId(null);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not rename conversation");
    }
  }

  async function sendMessage(
    event?: FormEvent<HTMLFormElement>,
    textOverride?: string,
    conversationIdOverride?: string
  ) {
    if (event) event.preventDefault();
    if (configuredProviders.length === 0) {
      setIsApiKeyWarningOpen(true);
      return;
    }
    const content = textOverride ?? draft.trim();
    const targetId = conversationIdOverride ?? activeConversationId;
    if (!targetId || !content) return;

    const api = createApiClient(getToken);
    setIsSending(true);
    setDraft("");
    setStatus("Planner is working");

    try {
      const response = await api<{
        job_id: string;
        status: string;
        user_message: Message;
      }>(`/conversations/${targetId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });

      const currentConv = conversations.find((c) => c.id === targetId);
      if (
        currentConv &&
        (currentConv.title.toLowerCase().startsWith("new session") ||
          currentConv.title.toLowerCase().startsWith("new chat") ||
          messages.length === 0)
      ) {
        const autoTitle = content.trim().slice(0, 30) + (content.trim().length > 30 ? "..." : "");
        void renameConversation(targetId, autoTitle);
      }

      if (targetId === activeConversationId || (!activeConversationId && targetId)) {
        setMessages((current) => [...current, response.user_message]);
      }

      const jobId = response.job_id;

      pollJob(
        async () => {
          const job = await api<{
            job_id: string;
            status: string;
            assistant_message: Message | null;
            error: string | null;
          }>(`/conversations/${targetId}/messages/jobs/${jobId}`);

          const succeeded = job.status === "succeeded" && job.assistant_message !== null;
          const failed = job.status === "failed";

          return {
            status: job.status,
            succeeded,
            failed,
            data: job.assistant_message ?? undefined,
            error: job.error ?? undefined,
          };
        },
        {
          intervalMs: 1000,
          timeoutMs: 60000,
          onTimeout: () => {
            setStatus("Planner timed out after 60 seconds");
            setIsSending(false);
          },
          onSucceeded: (assistantMessage) => {
            if (targetId === activeConversationId) {
              setMessages((current) => [...current, assistantMessage]);
            }
            setStatus(
              assistantMessage.tool_name ? `Used ${assistantMessage.tool_name}` : "Ready"
            );
            setIsSending(false);
            void loadConversations();
          },
          onFailed: (error) => {
            const message = error ?? "Planner failed";
            setStatus(message);
            toast.error(`Error: ${message}`);
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
          },
        }
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Planner failed";
      setStatus(message);
      toast.error(`Error: ${message}`);
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

  return (
    <ConversationContext.Provider
      value={{
        conversations,
        setConversations,
        activeConversationId,
        setActiveConversationId,
        messages,
        setMessages,
        editingConversationId,
        setEditingConversationId,
        editingTitle,
        setEditingTitle,
        conversationGroups,
        loadConversations,
        loadMessages,
        createConversation,
        deleteConversation,
        renameConversation,
        sendMessage,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
};

export function useConversations() {
  const context = useContext(ConversationContext);
  if (context === undefined) {
    throw new Error("useConversations must be used within a ConversationProvider");
  }
  return context;
}

export { ConversationContext };
