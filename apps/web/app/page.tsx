"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

type Message = {
  id: string;
  role: string;
  content: string;
  tool_name: string | null;
  created_at: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("Ready");
  const [isSending, setIsSending] = useState(false);
  const [apiKeyProvider, setApiKeyProvider] = useState<"gemini" | "groq">("gemini");
  const [apiKeyValue, setApiKeyValue] = useState("");
  const [apiKeyStatus, setApiKeyStatus] = useState("No key saved in this session");
  const [isSavingApiKey, setIsSavingApiKey] = useState(false);
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentContent, setDocumentContent] = useState("");
  const [documentStatus, setDocumentStatus] = useState("No knowledge uploaded");
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId),
    [activeConversationId, conversations],
  );
  const statusIsError = /failed|could not|error|invalid|502|503|401|embedding|provider/i.test(status);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("ai-os-token");
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  useEffect(() => {
    if (token) {
      void loadConversations(token);
    }
  }, [token]);

  useEffect(() => {
    if (token && activeConversationId) {
      void loadMessages(token, activeConversationId);
    }
  }, [activeConversationId, token]);

  async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
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
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Authentication failed");
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
      setActiveConversationId((current) => current ?? data[0]?.id ?? null);
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

  async function createConversation() {
    setStatus("Creating conversation");
    try {
      const conversation = await api<Conversation>("/conversations", {
        method: "POST",
        body: JSON.stringify({ title: "Planner session" }),
      });
      setConversations((current) => [conversation, ...current]);
      setActiveConversationId(conversation.id);
      setMessages([]);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create conversation");
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeConversationId || !draft.trim()) {
      return;
    }
    const content = draft.trim();
    setIsSending(true);
    setDraft("");
    setStatus("Planner is working");
    try {
      const response = await api<{ user_message: Message; assistant_message: Message }>(
        `/conversations/${activeConversationId}/messages`,
        {
          method: "POST",
          body: JSON.stringify({ content }),
        },
      );
      setMessages((current) => [...current, response.user_message, response.assistant_message]);
      setStatus(response.assistant_message.tool_name ? `Used ${response.assistant_message.tool_name}` : "Ready");
      void loadConversations(token as string);
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
    } finally {
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
      setApiKeyStatus(`${response.provider} key saved`);
    } catch (error) {
      setApiKeyStatus(error instanceof Error ? error.message : "Could not save key");
    } finally {
      setIsSavingApiKey(false);
    }
  }

  async function deleteApiKey() {
    setIsSavingApiKey(true);
    setApiKeyStatus("Deleting key");
    try {
      await api(`/users/me/api-keys/${apiKeyProvider}`, {
        method: "DELETE",
      });
      setApiKeyValue("");
      setApiKeyStatus(`${apiKeyProvider} key deleted`);
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
    setDocumentStatus("Embedding knowledge");
    try {
      const response = await api<{ title: string; chunk_count: number }>("/documents", {
        method: "POST",
        body: JSON.stringify({ title: documentTitle.trim(), content: documentContent.trim() }),
      });
      setDocumentTitle("");
      setDocumentContent("");
      setDocumentStatus(`${response.title} saved (${response.chunk_count} chunks)`);
    } catch (error) {
      setDocumentStatus(error instanceof Error ? error.message : "Could not upload knowledge");
    } finally {
      setIsUploadingDocument(false);
    }
  }

  function logout() {
    window.localStorage.removeItem("ai-os-token");
    setToken(null);
    setConversations([]);
    setMessages([]);
    setActiveConversationId(null);
    setStatus("Signed out");
  }

  if (!token) {
    return (
      <main className="auth-shell">
        <form className="auth-panel" onSubmit={handleAuth}>
          <p className="eyebrow">AI OS Phase 1</p>
          <h1>Sign in to the planner workspace</h1>
          <label>
            Email
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={mode === "register" ? 8 : 1}
              required
            />
          </label>
          <div className="auth-actions">
            <button type="submit">{mode === "login" ? "Login" : "Create account"}</button>
            <button type="button" className="ghost" onClick={() => setMode(mode === "login" ? "register" : "login")}>
              {mode === "login" ? "Register" : "Use login"}
            </button>
          </div>
          <p className="status">{status}</p>
        </form>
      </main>
    );
  }

  return (
    <main className="workspace">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">AI OS</p>
          <h1>Planner</h1>
        </div>
        <button type="button" onClick={createConversation}>New chat</button>
        <nav className="conversation-list" aria-label="Conversations">
          {conversations.map((conversation) => (
            <button
              type="button"
              key={conversation.id}
              className={conversation.id === activeConversationId ? "active" : ""}
              onClick={() => setActiveConversationId(conversation.id)}
            >
              {conversation.title}
            </button>
          ))}
        </nav>
        <form className="api-key-panel" onSubmit={saveApiKey}>
          <div>
            <p className="eyebrow">API Keys</p>
            <h2>BYOK</h2>
          </div>
          <label>
            Provider
            <select
              value={apiKeyProvider}
              onChange={(event) => setApiKeyProvider(event.target.value as "gemini" | "groq")}
              disabled={isSavingApiKey}
            >
              <option value="gemini">Gemini</option>
              <option value="groq">Groq</option>
            </select>
          </label>
          <label>
            Key
            <input
              type="password"
              value={apiKeyValue}
              onChange={(event) => setApiKeyValue(event.target.value)}
              placeholder="Paste API key"
              autoComplete="off"
              disabled={isSavingApiKey}
            />
          </label>
          <div className="api-key-actions">
            <button type="submit" disabled={isSavingApiKey || !apiKeyValue.trim()}>
              Save
            </button>
            <button type="button" className="ghost" onClick={deleteApiKey} disabled={isSavingApiKey}>
              Delete
            </button>
          </div>
          <p className="status">{apiKeyStatus}</p>
        </form>
        <form className="knowledge-panel" onSubmit={uploadDocument}>
          <div>
            <p className="eyebrow">Knowledge</p>
            <h2>Pasted text</h2>
          </div>
          <label>
            Title
            <input
              value={documentTitle}
              onChange={(event) => setDocumentTitle(event.target.value)}
              placeholder="Project notes"
              disabled={isUploadingDocument}
            />
          </label>
          <label>
            Content
            <textarea
              value={documentContent}
              onChange={(event) => setDocumentContent(event.target.value)}
              placeholder="Paste knowledge..."
              disabled={isUploadingDocument}
            />
          </label>
          <button type="submit" disabled={isUploadingDocument || !documentTitle.trim() || !documentContent.trim()}>
            Save knowledge
          </button>
          <p className="status">{documentStatus}</p>
        </form>
        <button type="button" className="ghost" onClick={logout}>Logout</button>
      </aside>
      <section className="chat">
        <header className="chat-header">
          <div>
            <p className="eyebrow">Conversation</p>
            <h2>{activeConversation?.title ?? "No conversation selected"}</h2>
          </div>
          <p className={`status ${statusIsError ? "error" : ""}`}>{status}</p>
        </header>
        <div className="messages">
          {messages.length === 0 && !isSending ? (
            <div className="empty-state">Create or select a conversation, then ask the planner for help.</div>
          ) : (
            <>
              {messages.map((message) => (
                <article key={message.id} className={`message ${message.role}`}>
                  <span>{message.role}</span>
                  <p>{message.content}</p>
                  {message.tool_name ? <small>Tool: {message.tool_name}</small> : null}
                </article>
              ))}
              {isSending ? (
                <article className="message assistant pending">
                  <span>assistant</span>
                  <p>Planner is working...</p>
                </article>
              ) : null}
            </>
          )}
        </div>
        <form className="composer" onSubmit={sendMessage}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask the planner..."
            disabled={!activeConversationId || isSending}
          />
          <button type="submit" disabled={!activeConversationId || isSending || !draft.trim()}>
            Send
          </button>
        </form>
      </section>
    </main>
  );
}
