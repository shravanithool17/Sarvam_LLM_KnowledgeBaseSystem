import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastProvider } from './contexts/ToastContext';
import { DocumentProvider } from './contexts/DocumentContext';
import { MainLayout } from './components/layout/MainLayout';

import { Dashboard } from './pages/Dashboard';
import { Ingestion } from './pages/Ingestion';
import { KnowledgeExplorer } from './pages/KnowledgeExplorer';
import { ChunkInspector } from './pages/ChunkInspector';
import { Quality } from './pages/Quality';
import { Search } from './pages/Search';
import { ExportCenter } from './pages/ExportCenter';
import { DocumentLibrary } from './pages/DocumentLibrary';
import { Settings } from './pages/Settings';

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <DocumentProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="ingestion" element={<Ingestion />} />
              <Route path="knowledge" element={<KnowledgeExplorer />} />
              <Route path="chunks" element={<ChunkInspector />} />
              <Route path="quality" element={<Quality />} />
              <Route path="search" element={<Search />} />
              <Route path="exports" element={<ExportCenter />} />
              <Route path="documents" element={<DocumentLibrary />} />
              <Route path="settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </DocumentProvider>
    </ToastProvider>
  );
};

export default App;
