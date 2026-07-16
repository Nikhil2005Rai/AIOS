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
  const [mounted, setMounted] = useState(false);
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
  const [apiKeyStatus, setApiKeyStatus] = useState("Configure your API keys");
  const [isSavingApiKey, setIsSavingApiKey] = useState(false);
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentContent, setDocumentContent] = useState("");
  const [documentStatus, setDocumentStatus] = useState("No knowledge uploaded");
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);

  // ChatGPT UI Clone states
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [activeSettingsTab, setActiveSettingsTab] = useState<"general" | "keys" | "knowledge">("keys");
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId),
    [activeConversationId, conversations],
  );
  
  const statusIsError = /failed|could not|error|invalid|502|503|401|embedding|provider/i.test(status);

  // Set mounted client-side to prevent hydration mismatch errors
  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("ai-os-token");
    if (savedToken) {
      setToken(savedToken);
      fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${savedToken}` }
      })
      .then(res => res.json())
      .then(data => {
        if (data.email) {
          setEmail(data.email);
        }
      })
      .catch(err => console.error("Could not fetch user profile", err));
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

  // Load configured keys checklist status
  useEffect(() => {
    if (email) {
      const saved = localStorage.getItem(`ai-os-keys-${email}`);
      if (saved) {
        try {
          setConfiguredProviders(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse cached configured keys", e);
        }
      }
    }
  }, [email]);

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
        body: JSON.stringify({ title: `New session ${conversations.length + 1}` }),
      });
      setConversations((current) => [conversation, ...current]);
      setActiveConversationId(conversation.id);
      setMessages([]);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create conversation");
    }
  }

  async function deleteConversation(conversationId: string) {
    setStatus("Deleting conversation");
    try {
      await api(`/conversations/${conversationId}`, {
        method: "DELETE",
      });
    } catch (error) {
      console.warn("Backend conversation deletion failed or unsupported:", error);
    }

    const remaining = conversations.filter((c) => c.id !== conversationId);
    setConversations(remaining);
    if (activeConversationId === conversationId) {
      setActiveConversationId(remaining[0]?.id ?? null);
      setMessages([]);
    }
    setStatus("Ready");
  }

  async function renameConversation(conversationId: string, newTitle: string) {
    if (!newTitle.trim()) return;
    setStatus("Renaming");
    try {
      await api(`/conversations/${conversationId}`, {
        method: "PUT",
        body: JSON.stringify({ title: newTitle.trim() }),
      });
    } catch (error) {
      console.warn("Backend rename failed or unsupported:", error);
    }
    setConversations((current) =>
      current.map((c) => (c.id === conversationId ? { ...c, title: newTitle.trim() } : c))
    );
    setEditingConversationId(null);
    setStatus("Ready");
  }

  async function sendMessage(event?: FormEvent<HTMLFormElement>, textOverride?: string) {
    if (event) event.preventDefault();
    const content = textOverride ?? draft.trim();
    if (!activeConversationId || !content) {
      return;
    }
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
      setApiKeyStatus(`${response.provider.toUpperCase()} API key saved successfully`);
      
      const nextProviders = [...new Set([...configuredProviders, apiKeyProvider])];
      setConfiguredProviders(nextProviders);
      if (email) {
        localStorage.setItem(`ai-os-keys-${email}`, JSON.stringify(nextProviders));
      }
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
      if (email) {
        localStorage.setItem(`ai-os-keys-${email}`, JSON.stringify(nextProviders));
      }
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

  // Group conversations by time headers
  const conversationGroups = useMemo(() => {
    const groups: { [key: string]: Conversation[] } = {
      Today: [],
      Yesterday: [],
      "Previous 7 Days": [],
      Older: [],
    };

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    conversations.forEach((c) => {
      const cDate = new Date(c.updated_at || c.created_at);
      if (cDate >= today) {
        groups.Today.push(c);
      } else if (cDate >= yesterday) {
        groups.Yesterday.push(c);
      } else if (cDate >= sevenDaysAgo) {
        groups["Previous 7 Days"].push(c);
      } else {
        groups.Older.push(c);
      }
    });

    return Object.entries(groups).filter(([_, items]) => items.length > 0);
  }, [conversations]);

  const suggestionCards = [
    {
      title: "Plan itinerary",
      desc: "Design a 3-day history trip to Rome",
      prompt: "Create a detailed 3-day itinerary exploring historical landmarks in Rome."
    },
    {
      title: "SQL Schema",
      desc: "Create order schema for e-commerce",
      prompt: "Design a PostgreSQL schema for an e-commerce catalog with users, products, orders, and review ratings."
    },
    {
      title: "FastAPI tests",
      desc: "Write pytest for JWT authentication",
      prompt: "Write clean pytest unit tests for a FastAPI endpoints module using mock users and JWT dependency overrides."
    },
    {
      title: "RAG Specs",
      desc: "Explain pgvector index parameters",
      prompt: "Explain the difference between HNSW and IVFFlat vector indexes in PostgreSQL pgvector, detailing pros/cons."
    }
  ];

  if (!mounted) return null;

  if (!token) {
    return (
      <main className="auth-shell">
        <form className="auth-panel" onSubmit={handleAuth}>
          <div className="brand-badge">Ω</div>
          <p className="eyebrow">ChatGPT OS Portal</p>
          <h1>Access workspace</h1>
          <p className="auth-desc">Universal AI Enterprise Orchestration Workspace</p>
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
              {mode === "login" ? "Create Account Instead" : "Sign In Instead"}
            </button>
          </div>
          {status !== "Ready" && status !== "Signed out" && (
            <p className={`status ${statusIsError ? "error" : ""}`}>{status}</p>
          )}
        </form>
      </main>
    );
  }

  return (
    <main className="workspace">
      {/* ChatGPT Styled Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <button type="button" className="new-chat-btn" onClick={createConversation}>
            <span>ChatGPT Clone</span>
            <span className="plus-icon">📝</span>
          </button>
        </div>

        {/* Date Grouped Chat History */}
        <div className="history-section">
          {conversations.length === 0 ? (
            <div className="empty-sidebar-state">No chat sessions yet.</div>
          ) : (
            conversationGroups.map(([groupName, items]) => (
              <div key={groupName} className="history-group">
                <h4 className="history-group-title">{groupName}</h4>
                <div className="history-group-list">
                  {items.map((conversation) => {
                    const isEditing = editingConversationId === conversation.id;
                    const isActive = conversation.id === activeConversationId;
                    return (
                      <div
                        key={conversation.id}
                        className={`conversation-item ${isActive ? "active" : ""}`}
                      >
                        {isEditing ? (
                          <input
                            type="text"
                            className="rename-input"
                            value={editingTitle}
                            onChange={(e) => setEditingTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                void renameConversation(conversation.id, editingTitle);
                              } else if (e.key === "Escape") {
                                setEditingConversationId(null);
                              }
                            }}
                            autoFocus
                            onBlur={() => void renameConversation(conversation.id, editingTitle)}
                          />
                        ) : (
                          <>
                            <button
                              type="button"
                              className="conv-select-btn"
                              onClick={() => setActiveConversationId(conversation.id)}
                            >
                              {conversation.title}
                            </button>
                            <div className="item-actions">
                              <button
                                type="button"
                                className="action-icon-btn"
                                title="Rename Chat"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setEditingConversationId(conversation.id);
                                  setEditingTitle(conversation.title);
                                }}
                              >
                                ✏️
                              </button>
                              <button
                                type="button"
                                className="action-icon-btn delete"
                                title="Delete Chat"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  void deleteConversation(conversation.id);
                                }}
                              >
                                🗑️
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Profile / Settings Footer */}
        <div className="sidebar-footer">
          <button
            type="button"
            className="footer-profile-btn"
            onClick={() => {
              setActiveSettingsTab("keys");
              setIsSettingsOpen(true);
            }}
          >
            <div className="profile-avatar">U</div>
            <div className="profile-details">
              <span className="profile-name">{email || "User Profile"}</span>
              <span className="profile-subtext">Settings & API Keys</span>
            </div>
          </button>
          <button type="button" className="ghost logout-btn-sidebar" onClick={logout}>
            Logout
          </button>
        </div>
      </aside>

      {/* Main viewport */}
      <section className="main-viewport">
        <div className="chat">
          {/* Top Navbar */}
          <header className="chat-header">
            <div className="header-left">
              <span className="model-selector">ChatGPT 4o-mini</span>
            </div>
            <div className="header-right">
              <p className={`status ${statusIsError ? "error" : ""}`}>{status}</p>
            </div>
          </header>

          {/* Messages view */}
          <div className="messages">
            {messages.length === 0 && !isSending ? (
              /* Welcome Page */
              <div className="empty-state">
                <div className="brand-badge-large">Ω</div>
                <h2>What can I help with today?</h2>
                
                {/* Suggestions Grid */}
                <div className="suggestions-grid">
                  {suggestionCards.map((card, idx) => (
                    <button
                      type="button"
                      key={idx}
                      className="suggestion-card"
                      onClick={() => {
                        setDraft(card.prompt);
                        void sendMessage(undefined, card.prompt);
                      }}
                    >
                      <h5>{card.title}</h5>
                      <p>{card.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Conversation list */
              messages.map((message) => {
                const isUser = message.role === "user";
                return (
                  <div key={message.id} className={`message-group ${isUser ? "user-group" : "assistant-group"}`}>
                    <div className={`message-avatar ${isUser ? "user-avatar" : "assistant-avatar"}`}>
                      {isUser ? "U" : "Ω"}
                    </div>
                    
                    <div className="message-bubble-wrapper">
                      <article className="message-bubble">
                        <span>{isUser ? "You" : "AI Assistant"}</span>
                        <p>{message.content}</p>
                        
                        {message.tool_name && (
                          <div className="tool-pill">
                            <span className="tool-icon">🛠️</span>
                            <span>Used Tool: <code>{message.tool_name}</code></span>
                          </div>
                        )}
                      </article>
                      
                      {!isUser && (
                        <div className="message-actions">
                          <button
                            type="button"
                            className="action-btn"
                            title="Copy output"
                            onClick={() => navigator.clipboard.writeText(message.content)}
                          >
                            📋 Copy
                          </button>
                          <button type="button" className="action-btn" title="Helpful">👍</button>
                          <button type="button" className="action-btn" title="Not helpful">👎</button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {isSending && (
              <div className="message-group assistant-group pending-group">
                <div className="message-avatar assistant-avatar">Ω</div>
                <div className="message-bubble-wrapper">
                  <article className="message-bubble pending-bubble">
                    <span>AI Assistant</span>
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <p className="pending-text">Planner is executing agent workflow nodes...</p>
                  </article>
                </div>
              </div>
            )}
          </div>

          {/* Composer Container */}
          <form className="composer-container" onSubmit={(e) => void sendMessage(e)}>
            <div className="composer-box">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Message ChatGPT..."
                disabled={!activeConversationId || isSending}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    e.currentTarget.form?.requestSubmit();
                  }
                }}
              />
              <div className="composer-actions">
                <span className="composer-hints">Press Enter to send, Shift+Enter for new line</span>
                <button
                  type="submit"
                  className="send-arrow-btn"
                  disabled={!activeConversationId || isSending || !draft.trim()}
                  title="Send message"
                >
                  ↑
                </button>
              </div>
            </div>
          </form>
        </div>
      </section>

      {/* Floating Settings Modal */}
      {isSettingsOpen && (
        <div className="modal-backdrop" onClick={() => setIsSettingsOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            {/* Modal Sidebar tabs */}
            <div className="modal-sidebar">
              <h3>Settings</h3>
              <nav className="modal-nav">
                <button
                  type="button"
                  className={`modal-nav-btn ${activeSettingsTab === "keys" ? "active" : ""}`}
                  onClick={() => setActiveSettingsTab("keys")}
                >
                  🔑 API Keys (BYOK)
                </button>
                <button
                  type="button"
                  className={`modal-nav-btn ${activeSettingsTab === "knowledge" ? "active" : ""}`}
                  onClick={() => setActiveSettingsTab("knowledge")}
                >
                  📚 Knowledge Hub
                </button>
                <button
                  type="button"
                  className={`modal-nav-btn ${activeSettingsTab === "general" ? "active" : ""}`}
                  onClick={() => setActiveSettingsTab("general")}
                >
                  ⚙️ General Info
                </button>
              </nav>
            </div>

            {/* Modal Content panels */}
            <div className="modal-body">
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setIsSettingsOpen(false)}
              >
                ✕
              </button>

              {/* API Keys Tab */}
              {activeSettingsTab === "keys" && (
                <div className="modal-tab-panel">
                  <h2>API Keys (BYOK)</h2>
                  <p className="tab-description">
                    Configure your credentials for model adapters. Your keys are stored encrypted locally.
                  </p>

                  <div className="settings-layout">
                    <form className="api-key-panel-modal" onSubmit={saveApiKey}>
                      <label>
                        LLM Provider
                        <select
                          value={apiKeyProvider}
                          onChange={(event) => setApiKeyProvider(event.target.value as "gemini" | "groq")}
                          disabled={isSavingApiKey}
                        >
                          <option value="gemini">Google Gemini</option>
                          <option value="groq">Groq Client</option>
                        </select>
                      </label>
                      <label>
                        Secret Key
                        <input
                          type="password"
                          value={apiKeyValue}
                          onChange={(event) => setApiKeyValue(event.target.value)}
                          placeholder={`Paste ${apiKeyProvider.toUpperCase()} api key`}
                          autoComplete="off"
                          disabled={isSavingApiKey}
                        />
                      </label>
                      <div className="actions-row-modal">
                        <button type="submit" disabled={isSavingApiKey || !apiKeyValue.trim()}>
                          {isSavingApiKey ? "Saving..." : "Save Key"}
                        </button>
                      </div>
                      {apiKeyStatus !== "Configure your API keys" && (
                        <p className="status">{apiKeyStatus}</p>
                      )}
                    </form>

                    <div className="key-status-list">
                      <h4>Connection Checklist</h4>
                      <div className="key-checklist">
                        <div className="checklist-item">
                          <div className="provider-status-info">
                            <span className={`status-dot ${configuredProviders.includes("gemini") ? "active" : ""}`}></span>
                            <div>
                              <h5>Google Gemini</h5>
                              <span>{configuredProviders.includes("gemini") ? "Active" : "Not Found"}</span>
                            </div>
                          </div>
                          {configuredProviders.includes("gemini") && (
                            <button
                              type="button"
                              className="ghost btn-delete-key"
                              onClick={() => deleteApiKey("gemini")}
                              disabled={isSavingApiKey}
                            >
                              Revoke
                            </button>
                          )}
                        </div>

                        <div className="checklist-item">
                          <div className="provider-status-info">
                            <span className={`status-dot ${configuredProviders.includes("groq") ? "active" : ""}`}></span>
                            <div>
                              <h5>Groq Client</h5>
                              <span>{configuredProviders.includes("groq") ? "Active" : "Not Found"}</span>
                            </div>
                          </div>
                          {configuredProviders.includes("groq") && (
                            <button
                              type="button"
                              className="ghost btn-delete-key"
                              onClick={() => deleteApiKey("groq")}
                              disabled={isSavingApiKey}
                            >
                              Revoke
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Knowledge Hub Tab */}
              {activeSettingsTab === "knowledge" && (
                <div className="modal-tab-panel">
                  <h2>Knowledge Hub (RAG)</h2>
                  <p className="tab-description">
                    Upload documents to index into your personal retrieval-augmented memory.
                  </p>
                  <form className="knowledge-panel-modal" onSubmit={uploadDocument}>
                    <label>
                      Title
                      <input
                        value={documentTitle}
                        onChange={(event) => setDocumentTitle(event.target.value)}
                        placeholder="Specification notes"
                        disabled={isUploadingDocument}
                        required
                      />
                    </label>
                    <label>
                      Content Body
                      <textarea
                        value={documentContent}
                        onChange={(event) => setDocumentContent(event.target.value)}
                        placeholder="Paste document reference text here..."
                        disabled={isUploadingDocument}
                        required
                      />
                    </label>
                    <button type="submit" disabled={isUploadingDocument || !documentTitle.trim() || !documentContent.trim()}>
                      {isUploadingDocument ? "Embedding document chunks..." : "Index Document"}
                    </button>
                    {documentStatus !== "No knowledge uploaded" && (
                      <p className="status">{documentStatus}</p>
                    )}
                  </form>
                </div>
              )}

              {/* General Tab */}
              {activeSettingsTab === "general" && (
                <div className="modal-tab-panel">
                  <h2>General Info</h2>
                  <p className="tab-description">Workspace configurations and session parameters.</p>
                  <div className="general-details-list">
                    <div className="detail-row">
                      <span>Email Account:</span>
                      <strong>{email}</strong>
                    </div>
                    <div className="detail-row">
                      <span>Workspace status:</span>
                      <strong>Active (Cloud Neon Sandbox)</strong>
                    </div>
                    <div className="detail-row">
                      <span>Interface:</span>
                      <strong>ChatGPT v4 Clone Interface</strong>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
