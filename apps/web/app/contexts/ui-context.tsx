"use client";

import React, { createContext, useContext, useState } from "react";

type UiContextType = {
  sidebarWidth: number;
  setSidebarWidth: (width: number) => void;
  isSidebarCollapsed: boolean;
  setIsSidebarCollapsed: (collapsed: boolean) => void;
  isSettingsOpen: boolean;
  setIsSettingsOpen: (open: boolean) => void;
  isApiKeyWarningOpen: boolean;
  setIsApiKeyWarningOpen: (open: boolean) => void;
  activeSettingsTab: "general" | "keys" | "knowledge";
  setActiveSettingsTab: (tab: "general" | "keys" | "knowledge") => void;
  draft: string;
  setDraft: (draft: string) => void;
  status: string;
  setStatus: (status: string) => void;
  isSending: boolean;
  setIsSending: (sending: boolean) => void;
};

const UiContext = createContext<UiContextType | undefined>(undefined);

export const UiProvider = ({ children }: { children: React.ReactNode }) => {
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isApiKeyWarningOpen, setIsApiKeyWarningOpen] = useState(false);
  const [activeSettingsTab, setActiveSettingsTab] = useState<"general" | "keys" | "knowledge">("keys");
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("Ready");
  const [isSending, setIsSending] = useState(false);

  return (
    <UiContext.Provider
      value={{
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
        setStatus,
        isSending,
        setIsSending,
      }}
    >
      {children}
    </UiContext.Provider>
  );
};

export function useUi() {
  const context = useContext(UiContext);
  if (context === undefined) {
    throw new Error("useUi must be used within a UiProvider");
  }
  return context;
}

export { UiContext };
