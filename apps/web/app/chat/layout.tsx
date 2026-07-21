"use client";

import React, { useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useChat } from "../chat-context";
import {
  ChevronLeft,
  Menu,
  Plus,
  Edit2,
  Trash2,
  User,
  LogOut,
  X,
  Key,
  BookOpen,
  Info,
  AlertTriangle,
  Search,
  Paperclip,
  Smile,
  SendHorizontal
} from "lucide-react";
import { authClient } from "../../lib/auth-client";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const {
    token,
    mounted,
    conversations,
    activeConversationId,
    setActiveConversationId,
    sidebarWidth,
    setSidebarWidth,
    isSidebarCollapsed,
    setIsSidebarCollapsed,
    isSettingsOpen,
    setIsSettingsOpen,
    isApiKeyWarningOpen,
    setIsApiKeyWarningOpen,
    activeSettingsTab,
    setActiveSettingsTab,
    draft,
    setDraft,
    status,
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
    isUploadingDocument,
    documents,
    configuredProviders,
    preferredProvider,
    editingConversationId,
    setEditingConversationId,
    editingTitle,
    setEditingTitle,
    logout,
    activeModelLabel,
    conversationGroups,
    sendMessage,
    createConversation,
    deleteConversation,
    renameConversation,
    saveApiKey,
    deleteApiKey,
    uploadDocument,
  } = useChat();

  const { data: session } = authClient.useSession();

  const startResizing = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = sidebarWidth;

    const handleMouseMove = (moveEvent: globalThis.MouseEvent) => {
      const newWidth = startWidth + (moveEvent.clientX - startX);
      if (newWidth >= 180 && newWidth <= 450) {
        setSidebarWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  useEffect(() => {
    if (mounted && !token) {
      router.replace("/auth");
    }
  }, [mounted, token, router]);

  if (!mounted) return null;
  if (!token) return null;

  return (
    <main
      className="workspace"
      style={{
        gridTemplateColumns: isSidebarCollapsed ? "1fr" : `${sidebarWidth}px 4px 1fr`,
        display: "grid",
        height: "100vh",
        width: "100vw",
        overflow: "hidden"
      }}
    >
      {/* Resizable Sidebar */}
      <aside
        className={`sidebar ${isSidebarCollapsed ? "collapsed" : ""}`}
        style={{
          width: isSidebarCollapsed ? "0px" : `${sidebarWidth}px`,
          height: "100%",
          display: isSidebarCollapsed ? "none" : "flex",
          flexDirection: "column",
          flexShrink: 0
        }}
      >
        <div className="sidebar-header">
          <div className="sidebar-header-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div className="sidebar-logo">Archimedes</div>
            <button
              type="button"
              className="sidebar-collapse-btn"
              title="Collapse Sidebar"
              onClick={() => setIsSidebarCollapsed(true)}
              style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
            >
              <ChevronLeft size={16} />
            </button>
          </div>
          <button type="button" className="new-chat-btn" onClick={createConversation}>
            <span>New Chat</span>
            <Plus size={16} />
          </button>
        </div>

        {/* Grouped History List */}
        <div className="history-section" style={{ flex: 1, overflowY: "auto" }}>
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
                              onClick={() => {
                                setActiveConversationId(conversation.id);
                                router.replace(`/chat/${conversation.id}`);
                              }}
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
                                <Edit2 size={12} />
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
                                <Trash2 size={12} />
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

        {/* Profile Footer */}
        <div className="sidebar-footer">
          <button
            type="button"
            className="footer-profile-btn"
            onClick={() => {
              setActiveSettingsTab("keys");
              setIsSettingsOpen(true);
            }}
          >
            <div className="profile-avatar">
              <User size={16} />
            </div>
            <div className="profile-details">
              <span className="profile-welcome">Welcome back,</span>
              <span className="profile-name">{session?.user?.email ? session.user.email.split('@')[0] : "User"}</span>
            </div>
          </button>
          <button type="button" className="ghost logout-btn-sidebar" onClick={logout}>
            <LogOut size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />
            Logout
          </button>
        </div>
      </aside>

      {/* Resize Handle */}
      {!isSidebarCollapsed && (
        <div
          className="sidebar-resize-handle"
          onMouseDown={startResizing}
          style={{ width: "4px", cursor: "col-resize", height: "100%" }}
        />
      )}

      {/* Main Chat Frame */}
      <section className="main-viewport" style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
        <div className="chat" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
          
          {/* Top Header Navbar */}
          <header className="chat-header">
            <div className="header-left">
              {isSidebarCollapsed && (
                <button
                  type="button"
                  className="sidebar-expand-btn"
                  title="Expand Sidebar"
                  onClick={() => setIsSidebarCollapsed(false)}
                  style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
                >
                  <Menu size={16} />
                </button>
              )}
              <span className="model-selector">{activeModelLabel}</span>
            </div>
            <div className="header-right">
              {status !== "Ready" && <p className={`status ${status.toLowerCase().includes("fail") || status.toLowerCase().includes("error") ? "error" : ""}`}>{status}</p>}
              <div className="header-tools">
                <span className="header-warning-icon" title="Archimedes Workspace Alert" style={{ display: "flex", alignItems: "center" }}>
                  <AlertTriangle size={14} style={{ color: "#eab308" }} />
                </span>
                {activeConversationId && (
                  <button
                    type="button"
                    className="header-tool-btn"
                    title="Delete Chat"
                    onClick={() => void deleteConversation(activeConversationId)}
                    style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
                  >
                    <Trash2 size={14} />
                  </button>
                )}
                <div className="header-search-capsule">
                  <input type="text" placeholder="Search..." />
                  <span className="search-icon" style={{ display: "flex", alignItems: "center" }}>
                    <Search size={12} />
                  </span>
                </div>
              </div>
            </div>
          </header>

          {/* Child Viewport Content (Message thread or Empty screen) */}
          <div style={{ flex: 1, overflowY: "auto" }}>
            {children}
          </div>

          {/* Composer Input Area */}
          <form className="composer-container" onSubmit={(e) => void sendMessage(e)}>
            <div className="composer-box">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Type a new message here..."
                disabled={!activeConversationId || isSending}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    e.currentTarget.form?.requestSubmit();
                  }
                }}
              />
              <div className="composer-toolbar-right">
                <button type="button" className="composer-icon-btn" title="Add attachment">
                  <Paperclip size={16} />
                </button>
                <button type="button" className="composer-icon-btn" title="Add emoji">
                  <Smile size={16} />
                </button>
                <button
                  type="submit"
                  className="composer-send-btn"
                  disabled={!activeConversationId || isSending || !draft.trim()}
                  title="Send message"
                  style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
                >
                  <SendHorizontal size={16} />
                </button>
              </div>
            </div>
            <div className="composer-actions">
              <span className="composer-hints">Press Enter to send, Shift+Enter for new line</span>
            </div>
          </form>
        </div>
      </section>

      {/* Floating Settings Modal */}
      {isSettingsOpen && (
        <div className="modal-backdrop" onClick={() => setIsSettingsOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-sidebar">
              <h3>Settings</h3>
              <nav className="modal-nav">
                <button
                  type="button"
                  className={`modal-nav-btn ${activeSettingsTab === "keys" ? "active" : ""}`}
                  onClick={() => setActiveSettingsTab("keys")}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  <Key size={14} />
                  <span>API Keys (BYOK)</span>
                </button>
                <button
                  type="button"
                  className={`modal-nav-btn ${activeSettingsTab === "knowledge" ? "active" : ""}`}
                  onClick={() => setActiveSettingsTab("knowledge")}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  <BookOpen size={14} />
                  <span>Knowledge Hub</span>
                </button>
                <button
                  type="button"
                  className={`modal-nav-btn ${activeSettingsTab === "general" ? "active" : ""}`}
                  onClick={() => setActiveSettingsTab("general")}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  <Info size={14} />
                  <span>General Info</span>
                </button>
              </nav>
            </div>

            <div className="modal-body">
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setIsSettingsOpen(false)}
                style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
              >
                <X size={16} />
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
                  <div className="settings-layout">
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

                    <div className="key-status-list">
                      <h4>Indexed Knowledge Bases</h4>
                      {documents.length === 0 ? (
                        <p className="no-keys-hint">No knowledge bases indexed yet.</p>
                      ) : (
                        <div className="key-checklist" style={{ maxHeight: "280px", overflowY: "auto" }}>
                          {documents.map((doc) => (
                            <div key={doc.id} className="checklist-item">
                              <div className="provider-status-info">
                                <span className="status-dot active"></span>
                                <div>
                                  <h5>{doc.title}</h5>
                                  <span>{doc.chunk_count} chunks • {new Date(doc.created_at).toLocaleDateString()}</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* General Settings Tab */}
              {activeSettingsTab === "general" && (
                <div className="modal-tab-panel">
                  <h2>Archimedes Orchestrator</h2>
                  <p className="tab-description">
                    Archimedes runs on a local/hybrid high-performance agent architecture.
                  </p>
                  <div className="general-details-card" style={{ padding: 16, background: "#f8fafc", border: "2px solid #000000", borderRadius: 8 }}>
                    <p style={{ margin: "0 0 8px 0" }}><strong>Platform Version:</strong> 1.2.0 (Stable)</p>
                    <p style={{ margin: "0 0 8px 0" }}><strong>Agent Framework:</strong> LangGraph Graph State Engine</p>
                    <p style={{ margin: "0 0 8px 0" }}><strong>Memory Type:</strong> Retrieval Augmented (pgvector)</p>
                    <p style={{ margin: 0 }}><strong>Decryption Engine:</strong> AES-256-CBC Fernet Cryptography</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* API Key Warning Modal */}
      {isApiKeyWarningOpen && (
        <div className="modal-backdrop" onClick={() => setIsApiKeyWarningOpen(false)}>
          <div className="modal-content" style={{ maxWidth: 400, padding: 24, textAlign: "center" }} onClick={(e) => e.stopPropagation()}>
            <AlertTriangle size={48} style={{ color: "#eab308", margin: "0 auto 16px" }} />
            <h2 style={{ marginBottom: 12 }}>API Key Required</h2>
            <p style={{ marginBottom: 24, color: "#64748b" }}>
              You need to configure an API key before you can chat or index documents.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <button
                type="button"
                className="ghost"
                onClick={() => setIsApiKeyWarningOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsApiKeyWarningOpen(false);
                  setActiveSettingsTab("keys");
                  setIsSettingsOpen(true);
                }}
              >
                Configure Key
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
