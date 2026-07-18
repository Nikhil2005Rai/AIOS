"use client";

import React, { useEffect } from "react";
import { useParams } from "next/navigation";
import { useChat } from "../../chat-context";
import { User, Bot, Wrench, Copy, ThumbsUp, ThumbsDown } from "lucide-react";

export default function ChatSessionPage() {
  const params = useParams();
  const chatId = params.id as string;
  
  const {
    token,
    messages,
    isSending,
    setActiveConversationId,
    loadMessages,
  } = useChat();

  useEffect(() => {
    if (chatId && token) {
      setActiveConversationId(chatId);
      void loadMessages(token, chatId);
    }
  }, [chatId, token]);

  return (
    <div className="messages">
      {messages.map((message) => {
        const isUser = message.role === "user";
        return (
          <div key={message.id} className={`message-group ${isUser ? "user-group" : "assistant-group"}`}>
            <div className={`message-avatar ${isUser ? "user-avatar" : "assistant-avatar"}`} style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
              {isUser ? <User size={16} /> : <Bot size={16} />}
            </div>
            
            <div className="message-bubble-wrapper">
              <article className="message-bubble">
                <span>{isUser ? "You" : "Archimedes"}</span>
                <p>{message.content}</p>
                
                {message.tool_name && (
                  <div className="tool-pill" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span className="tool-icon" style={{ display: "flex", alignItems: "center" }}>
                      <Wrench size={12} />
                    </span>
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
                    style={{ display: "flex", alignItems: "center", gap: 4 }}
                  >
                    <Copy size={12} />
                    <span>Copy</span>
                  </button>
                  <button type="button" className="action-btn" title="Helpful" style={{ display: "flex", alignItems: "center" }}>
                    <ThumbsUp size={12} />
                  </button>
                  <button type="button" className="action-btn" title="Not helpful" style={{ display: "flex", alignItems: "center" }}>
                    <ThumbsDown size={12} />
                  </button>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {isSending && (
        <div className="message-group assistant-group pending-group">
          <div className="message-avatar assistant-avatar" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Bot size={16} />
          </div>
          <div className="message-bubble-wrapper">
            <article className="message-bubble pending-bubble">
              <span>Archimedes</span>
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
  );
}
