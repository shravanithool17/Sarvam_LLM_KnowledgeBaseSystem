import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  PipelineResult,
  DocumentMetadata,
  ServerStatus,
  HealthCheck,
} from '../types';
import {
  fetchServerStatus,
  fetchHealthCheck,
  fetchDocumentList,
  fetchDocumentById,
  deleteDocumentById,
  getErrorMessage,
} from '../services/api';
import { useToast } from './ToastContext';

interface DocumentContextType {
  currentResult: PipelineResult | null;
  activeDocId: string | null;
  isProcessing: boolean;
  setIsProcessing: (val: boolean) => void;
  serverStatus: ServerStatus | null;
  healthCheck: HealthCheck | null;
  documents: DocumentMetadata[];
  setResult: (res: PipelineResult) => void;
  loadDocument: (docId: string) => Promise<PipelineResult | null>;
  deleteDocument: (docId: string) => Promise<boolean>;
  clearCurrentDocument: () => void;
  refreshStatus: () => Promise<void>;
  refreshDocuments: () => Promise<void>;
}

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

const STORAGE_KEY = 'llm_kn_active_pipeline';

export const DocumentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { showToast } = useToast();

  const [currentResult, setCurrentResultState] = useState<PipelineResult | null>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch {
      // Ignore parse error
    }
    return null;
  });

  const [activeDocId, setActiveDocId] = useState<string | null>(
    currentResult?.document_id || null
  );
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null);
  const [healthCheck, setHealthCheck] = useState<HealthCheck | null>(null);
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);

  const setResult = useCallback((result: PipelineResult) => {
    setCurrentResultState(result);
    if (result.document_id) {
      setActiveDocId(result.document_id);
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(result));
    } catch {
      // LocalStorage might be full
    }
  }, []);

  const clearCurrentDocument = useCallback(() => {
    setCurrentResultState(null);
    setActiveDocId(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const [statusData, healthData] = await Promise.allSettled([
        fetchServerStatus(),
        fetchHealthCheck(),
      ]);
      if (statusData.status === 'fulfilled') {
        setServerStatus(statusData.value);
      }
      if (healthData.status === 'fulfilled') {
        setHealthCheck(healthData.value);
      }
    } catch (err) {
      console.error('Failed to load status:', err);
    }
  }, []);

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await fetchDocumentList();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents list:', err);
    }
  }, []);

  const loadDocument = useCallback(
    async (docId: string): Promise<PipelineResult | null> => {
      try {
        setIsProcessing(true);
        const docResult = await fetchDocumentById(docId);
        setResult(docResult);
        showToast(`Loaded document "${docResult.document_name}"`, 'success');
        return docResult;
      } catch (err) {
        showToast(`Failed to load document: ${getErrorMessage(err)}`, 'error');
        return null;
      } finally {
        setIsProcessing(false);
      }
    },
    [setResult, showToast]
  );

  const deleteDocument = useCallback(
    async (docId: string): Promise<boolean> => {
      try {
        await deleteDocumentById(docId);
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
        if (activeDocId === docId) {
          clearCurrentDocument();
        }
        showToast('Document deleted successfully', 'success');
        return true;
      } catch (err) {
        showToast(`Failed to delete document: ${getErrorMessage(err)}`, 'error');
        return false;
      }
    },
    [activeDocId, clearCurrentDocument, showToast]
  );

  // Initial load
  useEffect(() => {
    refreshStatus();
    refreshDocuments();
  }, [refreshStatus, refreshDocuments]);

  return (
    <DocumentContext.Provider
      value={{
        currentResult,
        activeDocId,
        isProcessing,
        setIsProcessing,
        serverStatus,
        healthCheck,
        documents,
        setResult,
        loadDocument,
        deleteDocument,
        clearCurrentDocument,
        refreshStatus,
        refreshDocuments,
      }}
    >
      {children}
    </DocumentContext.Provider>
  );
};

export function useDocument(): DocumentContextType {
  const context = useContext(DocumentContext);
  if (!context) {
    throw new Error('useDocument must be used within a DocumentProvider');
  }
  return context;
}

