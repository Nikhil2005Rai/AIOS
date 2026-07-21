"use client";

import React, { createContext, useContext, useState, useEffect, FormEvent } from "react";
import { createApiClient } from "../lib/api-client";
import { useAuth } from "./auth-context";
import { pollJob } from "../hooks/use-job-poller";

export type DocumentBase = {
  id: string;
  title: string;
  chunk_count: number;
  created_at: string;
};

type DocumentsContextType = {
  documents: DocumentBase[];
  documentTitle: string;
  setDocumentTitle: (title: string) => void;
  documentContent: string;
  setDocumentContent: (content: string) => void;
  documentStatus: string;
  setDocumentStatus: (status: string) => void;
  isUploadingDocument: boolean;
  loadDocuments: (authToken: string) => Promise<void>;
  deleteDocument: (docId: string) => Promise<void>;
  uploadDocument: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

const DocumentsContext = createContext<DocumentsContextType | undefined>(undefined);

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const DocumentsProvider = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAuth();

  const [documents, setDocuments] = useState<DocumentBase[]>([]);
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentContent, setDocumentContent] = useState("");
  const [documentStatus, setDocumentStatus] = useState("No knowledge uploaded");
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);

  useEffect(() => {
    if (token) {
      void loadDocuments(token);
    }
  }, [token]);

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
    const api = createApiClient(token);
    try {
      await api(`/documents/${docId}`, { method: "DELETE" });
      setDocuments((current) => current.filter((doc) => doc.id !== docId));
    } catch (error) {
      console.error("Could not delete document", error);
    }
  }

  async function uploadDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!documentTitle.trim() || !documentContent.trim()) {
      setDocumentStatus("Add a title and content");
      return;
    }
    const api = createApiClient(token);
    setIsUploadingDocument(true);
    setDocumentStatus("Queued");

    try {
      const response = await api<{ job_id: string; status: string }>("/documents", {
        method: "POST",
        body: JSON.stringify({ title: documentTitle.trim(), content: documentContent.trim() }),
      });

      const jobId = response.job_id;

      pollJob(
        async () => {
          const job = await api<{
            job_id: string;
            status: string;
            result: { title: string; chunk_count: number } | null;
            error: string | null;
          }>(`/documents/jobs/${jobId}`);

          const succeeded = job.status === "succeeded";
          const failed = job.status === "failed";

          // Show intermediate statuses as they arrive
          if (job.status === "queued") {
            setDocumentStatus("Queued");
          } else if (job.status === "running") {
            setDocumentStatus("Embedding knowledge");
          }

          return {
            status: job.status,
            succeeded,
            failed,
            data: job.result ?? undefined,
            error: job.error ?? undefined,
          };
        },
        {
          intervalMs: 1500,
          timeoutMs: 120000,
          onTimeout: () => {
            setDocumentStatus("Ingestion timed out after 2 minutes");
            setIsUploadingDocument(false);
          },
          onSucceeded: (result) => {
            setDocumentTitle("");
            setDocumentContent("");
            setDocumentStatus(
              `${result?.title ?? "Document"} saved (${result?.chunk_count ?? 0} chunks)`
            );
            setIsUploadingDocument(false);
            if (token) void loadDocuments(token);
          },
          onFailed: (error) => {
            setDocumentStatus(`Ingestion failed: ${error}`);
            setIsUploadingDocument(false);
          },
        }
      );
    } catch (error) {
      setDocumentStatus(error instanceof Error ? error.message : "Could not upload knowledge");
      setIsUploadingDocument(false);
    }
  }

  return (
    <DocumentsContext.Provider
      value={{
        documents,
        documentTitle,
        setDocumentTitle,
        documentContent,
        setDocumentContent,
        documentStatus,
        setDocumentStatus,
        isUploadingDocument,
        loadDocuments,
        deleteDocument,
        uploadDocument,
      }}
    >
      {children}
    </DocumentsContext.Provider>
  );
};

export function useDocuments() {
  const context = useContext(DocumentsContext);
  if (context === undefined) {
    throw new Error("useDocuments must be used within a DocumentsProvider");
  }
  return context;
}

export { DocumentsContext };
