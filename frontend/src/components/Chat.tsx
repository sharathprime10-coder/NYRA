import React, { useRef, useEffect, useState } from 'react';
import ChatLayout from './layout/ChatLayout';
import { FolderOpen, ChevronDown, Paperclip, ArrowUp, Search, MessageSquare, BookOpen, FileText, Mic } from 'lucide-react';
import CinematicVoiceOrb from './CinematicVoiceOrb';
import { AnimatePresence } from 'framer-motion';
import api from '../api/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { useParams } from 'react-router-dom';

interface Source {
  document_id?: number;
  source?: string;
  page?: number;
  content: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'ai';
  content: string;
  sources?: Source[];
  confidence?: string;
}

const Chat: React.FC = () => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<number | undefined>(undefined);
  const [isRecording, setIsRecording] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | 'all'>('all');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { sessionId: routeSessionId } = useParams();

  useEffect(() => {
    api.get('/api/documents/').then(res => setDocuments(res.data)).catch(console.error);
  }, []);

  useEffect(() => {
    if (routeSessionId) {
      const sid = parseInt(routeSessionId);
      setSessionId(sid);
      
      setLoading(true);
      api.get(`/api/chat/${sid}`)
        .then(res => {
          setMessages(res.data.map((m: any) => ({
            id: m.id.toString(),
            role: m.role,
            content: m.content,
            sources: m.sources,
          })));
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    } else {
      setSessionId(undefined);
      setMessages([]);
    }
  }, [routeSessionId]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const handleInput = () => {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
      if (textarea.scrollHeight > 128) {
        textarea.style.overflowY = 'auto';
      } else {
        textarea.style.overflowY = 'hidden';
      }
    };

    textarea.addEventListener('input', handleInput);
    return () => textarea.removeEventListener('input', handleInput);
  }, []);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.post('/api/chat/', {
        message: userMessage.content,
        session_id: sessionId,
        filters: selectedDocumentId === 'all' ? undefined : { document_id: selectedDocumentId }
      });
      
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: res.data.answer,
        sources: res.data.sources,
        confidence: res.data.confidence
      };
      
      setMessages(prev => [...prev, aiMessage]);
      if (res.data.session_id) {
        setSessionId(res.data.session_id);
      }
    } catch (err) {
      console.error("Chat error", err);
      // Optional: add an error message to chat
    } finally {
      setLoading(false);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // In a real app, show upload progress. Here we just upload.
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      setLoading(true);
      await api.post('/api/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      // Add a system message or notification
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'ai',
        content: `I've successfully uploaded "${file.name}" to your knowledge base.`
      }]);
    } catch (err) {
      console.error("Upload error", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ChatLayout>
      {/* Chat Container */}
      <div className="w-full max-w-[900px] px-4 md:px-8 flex flex-col h-full relative z-10">
        
        {/* Chat Scroll Area */}
        <div className="flex-1 overflow-y-auto pb-40 pt-8 scrollbar-hide flex flex-col gap-8">
          
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center text-center opacity-50">
              <h3 className="font-display text-xl mb-2 text-on-surface">How can I help you today?</h3>
              <p className="font-body text-sm text-on-surface-variant max-w-sm">Ask NYRA anything based on the documents you've uploaded to your knowledge base.</p>
            </div>
          )}

          {messages.map((msg) => (
            msg.role === 'user' ? (
              <div key={msg.id} className="flex justify-end w-full">
                <div className="max-w-[80%] glass-advanced holographic-border rounded-2xl rounded-tr-sm p-4 text-on-surface hover-lock">
                  <div className="noise-overlay rounded-2xl rounded-tr-sm"></div>
                  <p className="whitespace-pre-wrap relative z-10">{msg.content}</p>
                </div>
              </div>
            ) : (
              <div key={msg.id} className="flex flex-col w-full gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full overflow-hidden border border-primary/30 flex items-center justify-center hover-lock">
                    <img alt="NYRA Logo" className="w-full h-full object-cover rounded-full" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCoL3dTGzoRQJtZDQUAs-KR2ltDQDYfekLVq2dHDjn7ArpriZCcQX_ZRORM5QVIqikIOfEFhJ4EJWRdsPZqwNWpyyfIftduM46v3nLmBRC9s0bi0SEfnZC2eDUuhXXo6WC-fX7tL3xKA5PBQnuUXkOgFOGd9sFFIWJxqjQV7EbRdqgSj4si_uIHUGRAkBYCz1VZ5JWu9BkEGezdk412gOmrToUWThu5SYwSPAECGuZvA6cMtl40hCwb4D4z-v8pCoxgAAA" />
                  </div>
                  <span className="font-display text-sm font-bold gradient-text">NYRA</span>
                </div>
                
                <div className="max-w-[90%] text-on-surface space-y-6">
                  <div className="prose prose-invert prose-p:leading-relaxed prose-pre:bg-surface-container-high prose-pre:border prose-pre:border-outline-variant/30 max-w-none font-body text-lg">
                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                  
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-6 mb-4">
                      <h4 className="font-label text-xs text-on-surface-variant uppercase tracking-wider mb-3 flex items-center gap-2">
                        <BookOpen className="w-4 h-4" />
                        Sourced Context
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {msg.sources.map((src, i) => (
                          <div key={i} className="glass-advanced holographic-border p-3 rounded-xl flex items-start gap-3 cursor-pointer group overflow-hidden">
                            <div className="noise-overlay rounded-xl"></div>
                            <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center flex-shrink-0 group-hover:bg-primary/20 transition-colors relative z-10">
                              <FileText className="text-tertiary w-5 h-5" />
                            </div>
                            <div className="overflow-hidden">
                              <p className="text-sm font-semibold text-on-surface truncate">{src.source || "Document"}</p>
                              <p className="text-xs text-on-surface-variant mt-1 truncate">{src.page ? `Page ${src.page}` : "Excerpt"}</p>
                            </div>
                            <div className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                              <button className="bg-primary/20 hover:bg-primary/30 text-primary text-[10px] font-bold px-2 py-1.5 rounded-md backdrop-blur-md border border-primary/30 flex items-center gap-1 hover-lock">
                                <MessageSquare className="w-3 h-3" /> Ask NYRA
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* RAG Confidence */}
                  {msg.confidence && (
                    <div className="flex items-center gap-3 mt-6 pt-4 border-t border-outline-variant/20 hover-lock rounded-lg p-2 -ml-2 cursor-default w-max">
                      <div className="flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${msg.confidence === 'High' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]' : msg.confidence === 'Medium' ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]' : 'bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.5)]'}`}></span>
                        <span className="font-label text-xs text-on-surface font-medium">{msg.confidence} Confidence</span>
                      </div>
                      <span className="text-on-surface-variant text-xs">•</span>
                      <span className="font-label text-xs text-on-surface-variant">
                        Answer grounded in {msg.sources?.length || 0} sources
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          ))}
          
          {loading && (
            <div className="flex items-center gap-3 mt-4 opacity-70">
              <div className="particle-orbiter w-6 h-6 flex items-center justify-center rounded-full bg-surface-container-high border border-outline-variant/30 hover-lock">
                <Search className="text-tertiary w-3.5 h-3.5" />
              </div>
              <span className="font-label text-xs text-tertiary animate-pulse font-semibold">NYRA is retrieving sources...</span>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
        
        {/* Composer (Floating Glass Container) */}
        <div className="absolute bottom-8 left-4 right-4 md:left-8 md:right-8 z-20">
          <div className="glass-advanced holographic-border rounded-2xl p-2 flex flex-col gap-2">
            <div className="noise-overlay rounded-2xl"></div>
            
            {/* Context Chips Area & Scope Selector */}
            <div className="px-3 pt-2 pb-1 flex justify-between items-center relative">
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="hover-lock flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-low border border-outline-variant/20 font-label text-xs font-semibold text-on-surface-variant hover:text-on-surface hover:border-outline-variant/40 transition-all">
                  <FolderOpen className="w-4 h-4" />
                  <span className="max-w-[150px] truncate">
                    {selectedDocumentId === 'all' ? 'All Documents' : documents.find(d => d.id === selectedDocumentId)?.filename || 'Document'}
                  </span>
                  <ChevronDown className="w-4 h-4" />
                </button>

                {isDropdownOpen && (
                  <div className="absolute bottom-full left-3 mb-2 bg-surface-container-high border border-outline-variant/30 rounded-lg shadow-xl overflow-hidden z-50 min-w-[200px] max-h-48 overflow-y-auto">
                    <button 
                      onClick={() => { setSelectedDocumentId('all'); setIsDropdownOpen(false); }}
                      className={`w-full text-left px-4 py-2 text-xs font-label hover:bg-primary/10 transition-colors ${selectedDocumentId === 'all' ? 'text-primary' : 'text-on-surface'}`}
                    >
                      All Documents
                    </button>
                    {documents.map(doc => (
                      <button 
                        key={doc.id}
                        onClick={() => { setSelectedDocumentId(doc.id); setIsDropdownOpen(false); }}
                        className={`w-full text-left px-4 py-2 text-xs font-label hover:bg-primary/10 transition-colors truncate ${selectedDocumentId === doc.id ? 'text-primary' : 'text-on-surface'}`}
                      >
                        {doc.filename}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            
            {!isRecording ? (
            <div className="flex items-end gap-2 px-2 pb-1">
              <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                onChange={handleFileUpload} 
              />
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="hover-lock w-10 h-10 rounded-xl hover:bg-surface-container transition-colors flex items-center justify-center text-on-surface-variant hover:text-primary shrink-0"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <div className="flex-1 min-h-[44px] bg-transparent flex items-center">
                <textarea 
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-transparent border-none text-on-surface placeholder-on-surface-variant resize-none focus:ring-0 max-h-32 overflow-y-auto font-body text-base py-3 outline-none" 
                  placeholder="Message NYRA..." 
                  rows={1}
                />
              </div>
              
              <button 
                onClick={() => setIsRecording(true)}
                className="hover-lock w-10 h-10 rounded-xl hover:bg-surface-container text-on-surface-variant flex items-center justify-center hover:text-tertiary transition-colors shrink-0 mb-1">
                <Mic className="w-5 h-5" />
              </button>

              <button 
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="hover-lock w-10 h-10 rounded-xl bg-primary text-on-primary flex items-center justify-center hover:bg-primary-container transition-colors shrink-0 mb-1 disabled:opacity-50 disabled:cursor-not-allowed">
                <ArrowUp className="w-5 h-5" />
              </button>
            </div>
            ) : (
              <AnimatePresence>
                {isRecording && (
                  <CinematicVoiceOrb 
                    onClose={() => setIsRecording(false)} 
                    sessionId={sessionId}
                    onMessageTranscribed={(msg, response, newSessionId) => {
                      // Append to chat history
                      setMessages(prev => [
                        ...prev,
                        { id: Date.now().toString(), role: 'user', content: msg },
                        { id: (Date.now() + 1).toString(), role: 'ai', content: response }
                      ]);
                      if (newSessionId) setSessionId(newSessionId);
                    }}
                  />
                )}
              </AnimatePresence>
            )}

          </div>
          <div className="text-center mt-3 text-[10px] text-on-surface-variant/60 font-medium tracking-wide">
            NYRA strives for accuracy, but may occasionally make mistakes. Please verify important information.
          </div>
        </div>
      </div>
    </ChatLayout>
  );
};

export default Chat;
