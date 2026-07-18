"use client";

import React, { useEffect } from "react";
import { useChat } from "../chat-context";

export default function EmptyChatPage() {
  const {
    activeConversationId,
    setActiveConversationId,
    setMessages,
    suggestionCards,
    setDraft,
    createConversation,
    sendMessage,
  } = useChat();

  useEffect(() => {
    setActiveConversationId(null);
    setMessages([]);
  }, []);

  return (
    <div className="empty-state">
      <div className="brand-badge-large">A</div>
      <h2>How can Archimedes assist you?</h2>
      
      {/* Suggestions Grid */}
      <div className="suggestions-grid">
        {suggestionCards.map((card, idx) => (
          <button
            type="button"
            key={idx}
            className="suggestion-card"
            onClick={async () => {
              setDraft(card.prompt);
              let targetId = activeConversationId;
              if (!targetId) {
                const newConv = await createConversation();
                if (!newConv) return;
                targetId = newConv.id;
              }
              void sendMessage(undefined, card.prompt, targetId);
            }}
          >
            <h5>{card.title}</h5>
            <p>{card.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
