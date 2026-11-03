import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  Send,
  Bot,
  User,
  Sparkles,
  Layers,
  RotateCcw,
  Copy,
  Check,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';
import { useDocument } from '../contexts/DocumentContext';
import { useToast } from '../contexts/ToastContext';
import { queryRAG, getErrorMessage } from '../services/api';
import { RAGResponse } from '../types';
import { EmptyState } from '../components/common/EmptyState';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  retrievedChunks?: RAGResponse['retrieved_chunks'];
  citations?: string[];
}

export const Search: React.FC = () => {
  const navigate = useNavigate();
  const { currentResult } = useDocument();
  const { showToast } = useToast();

  const [inputQuery, setInputQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSearching]);

  if (!currentResult || !currentResult.chunks.length) {
    return (
      <EmptyState
        title="No Document Loaded for Search"
        description="Please ingest a document first to enable real-time vector retrieval and grounded question answering with Sarvam AI."
        actionText="Go to Ingestion"
        onAction={() => navigate('/ingestion')}
      />
    );
  }

  const handleSendQuery = async (queryText?: string) => {
    const q = (queryText || inputQuery).trim();
    if (!q) {
      showToast('Please type a question to ask the document', 'warning');
      return;
    }

    const userMsg: ChatMessage = {
      id: Math.random().toString(36).substring(2, 9),
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsSearching(true);

    try {
      const response = await queryRAG({
        query: q,
        chunks: currentResult.chunks,
      });

      const assistantMsg: ChatMessage = {
        id: Math.random().toString(36).substring(2, 9),
        sender: 'assistant',
        text: response.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        retrievedChunks: response.retrieved_chunks,
        citations: response.citations,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      showToast(`Search failed: ${getErrorMessage(err)}`, 'error');
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendQuery();
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(id);
    showToast('Answer copied to clipboard', 'success');
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const suggestedQuestions = [
    'What is the primary problem statement and motivation?',
    'How does semantic boundary chunking work?',
    'What are the key findings or takeaways?',
    'How does the system ensure traceability of answers?',
  ];

  return (
    <div className="space-y-6 max-w-4xl mx-auto flex flex-col h-[calc(100vh-8.5rem)]">
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">AI Knowledge Search (RAG)</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-950/60 text-purple-300 border border-purple-800/40">
              Grounded Retrieval
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Grounded vector search over <strong className="text-slate-200">{currentResult.document_name}</strong> (
            {currentResult.chunks.length} chunks indexed).
          </p>
        </div>

        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white text-xs flex items-center gap-1.5 transition"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Clear Chat</span>
          </button>
        )}
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-2">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-6">
            <div className="w-16 h-16 rounded-3xl bg-purple-950/40 border border-purple-800/30 flex items-center justify-center text-purple-400">
              <MessageSquare className="w-8 h-8" />
            </div>

            <div className="max-w-md space-y-1">
              <h3 className="text-base font-bold text-slate-200">Ask Anything About This Document</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Sarvam AI retrieves the most relevant boundary-aware chunks and synthesizes a grounded answer with
                strict source citations.
              </p>
            </div>

            {/* Suggested prompts */}
            <div className="w-full max-w-lg space-y-2 pt-2">
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                Suggested Prompts
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {suggestedQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendQuery(q)}
                    className="p-3 rounded-xl border border-slate-800/80 bg-slate-900/50 hover:bg-purple-950/20 hover:border-purple-600/40 text-xs text-slate-300 hover:text-white transition group flex items-center justify-between"
                  >
                    <span className="line-clamp-2">{q}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-purple-400 shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 sm:gap-4 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.sender === 'assistant' && (
                <div className="w-8 h-8 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 sm:p-5 space-y-3 ${
                  msg.sender === 'user'
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20'
                    : 'glass-card border border-slate-800/80 text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between gap-4 text-[10px] opacity-70">
                  <span className="font-semibold uppercase tracking-wider">
                    {msg.sender === 'user' ? 'You' : 'Sarvam-105B Grounded Answer'}
                  </span>
                  <span>{msg.timestamp}</span>
                </div>

                <p className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>

                {/* Citations & Retrieved Context Cards */}
                {msg.sender === 'assistant' && msg.retrievedChunks && msg.retrievedChunks.length > 0 && (
                  <div className="pt-3 border-t border-slate-800/80 space-y-2">
                    <span className="text-[10px] font-mono text-purple-400 uppercase tracking-wider flex items-center gap-1 font-semibold">
                      <Layers className="w-3 h-3" />
                      Retrieved Context Sources ({msg.retrievedChunks.length})
                    </span>

                    <div className="grid grid-cols-1 gap-2 pt-1">
                      {msg.retrievedChunks.map((chunk) => (
                        <div
                          key={chunk.id}
                          className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between text-[11px] font-mono">
                            <span className="text-blue-400 font-bold">
                              {chunk.id} (Page {chunk.page})
                            </span>
                            <span className="text-purple-400 bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/40">
                              {chunk.relevance_score}% match
                            </span>
                          </div>
                          <p className="text-xs text-slate-300 leading-relaxed font-mono line-clamp-3 bg-slate-950/60 p-2 rounded border border-slate-900">
                            {chunk.text}
                          </p>
                        </div>
                      ))}
                    </div>

                    <div className="flex justify-end pt-1">
                      <button
                        onClick={() => handleCopy(msg.id, msg.text)}
                        className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1"
                      >
                        {copiedIndex === msg.id ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                        <span>{copiedIndex === msg.id ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {msg.sender === 'user' && (
                <div className="w-8 h-8 rounded-xl bg-slate-800 text-slate-300 border border-slate-700 flex items-center justify-center shrink-0 mt-1">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))
        )}

        {isSearching && (
          <div className="flex gap-3 items-center">
            <div className="w-8 h-8 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="glass-card px-4 py-3 rounded-2xl border border-slate-800 text-xs text-purple-300 flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-full border-2 border-purple-400 border-t-transparent animate-spin" />
              <span>Retrieving relevant chunks & formulating grounded response...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form Bar */}
      <div className="glass-card p-2.5 rounded-2xl border border-slate-800 shrink-0 flex items-center gap-2">
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about the document... (Press Enter)"
          className="flex-1 bg-transparent px-3 py-2 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none"
        />
        <button
          onClick={() => handleSendQuery()}
          disabled={!inputQuery.trim() || isSearching}
          className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-purple-600/20 transition disabled:opacity-40"
        >
          <span>Ask</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
