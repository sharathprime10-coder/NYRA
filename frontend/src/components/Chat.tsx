import React, { useRef, useEffect, useState } from 'react';
import ChatLayout from './layout/ChatLayout';
import { FolderOpen, ChevronDown, Paperclip, ArrowUp, Search, MessageSquare, BookOpen, FileText, Mic, Zap, Brain, BrainCircuit, ThumbsUp, Lightbulb } from 'lucide-react';
import CinematicVoiceOrb from './CinematicVoiceOrb';
import { AnimatePresence } from 'framer-motion';
import api from '../api/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { useParams } from 'react-router-dom';
import { useSpeechToText } from '../hooks/useSpeechToText';
import { PromptCoach } from './PromptCoach';


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
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [liveAgentStatus, setLiveAgentStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | 'all'>('all');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [thinkingLevel, setThinkingLevel] = useState<'low' | 'medium' | 'high'>('medium');
  const [isThinkingDropdownOpen, setIsThinkingDropdownOpen] = useState(false);
  const { sessionId: routeSessionId } = useParams();
  const [showCoach, setShowCoach] = useState(() => localStorage.getItem('nyra_show_coach') === 'true');
  const [optedInIds, setOptedInIds] = useState<Set<string>>(new Set());

  const handleOptIn = async (msgId: string, aiContent: string) => {
    if (optedInIds.has(msgId)) return;

    // Find the immediately preceding user message
    const msgIndex = messages.findIndex(m => m.id === msgId);
    let userQuery = "Unknown query";
    for (let i = msgIndex - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        userQuery = messages[i].content;
        break;
      }
    }

    try {
      await api.post('/api/curation/opt-in', {
        user_query: userQuery,
        ai_response: aiContent
      });
      setOptedInIds(prev => new Set(prev).add(msgId));
    } catch (err) {
      console.error("Failed to opt-in", err);
    }
  };
  
  // Save coach preference
  useEffect(() => {
    localStorage.setItem('nyra_show_coach', showCoach.toString());
  }, [showCoach]);
  
  const [inputBeforeMic, setInputBeforeMic] = useState('');
  const [isOrbOpen, setIsOrbOpen] = useState(false);
  
  const { isListening, supported: sttSupported, toggleListening } = useSpeechToText({
    onResult: (text, isFinal) => {
      setInput(inputBeforeMic + (inputBeforeMic && text ? ' ' : '') + text);
    }
  });
  
  const handleToggleMic = () => {
    setIsOrbOpen(true);
  };

  useEffect(() => {
    api.get('/api/documents/').then(res => setDocuments(res.data)).catch(console.error);
  }, []);

  useEffect(() => {
    if (routeSessionId) {
      setSessionId(routeSessionId);
      
      setLoading(true);
      api.get(`/api/chat/${routeSessionId}`)
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
    
    const aiMessageId = (Date.now() + 1).toString();
    
    setMessages(prev => [...prev, userMessage, { id: aiMessageId, role: 'ai', content: '' }]);
    setInput('');
    setLoading(true);
    setLiveAgentStatus('Connecting...');

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId,
          filters: selectedDocumentId === 'all' ? undefined : { document_id: selectedDocumentId },
          thinking_level: thinkingLevel,
          tone: localStorage.getItem('nyra_tone') === 'sassy' ? 'sassy' : 'default'
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (!reader) throw new Error("No reader available");

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.event === 'status') {
                const nodeStr = data.node === 'supervisor' ? 'Thinking...' :
                                data.node === 'researcher' ? 'Researching...' :
                                data.node === 'writer' ? 'Drafting...' :
                                data.node === 'critic' ? 'Reviewing...' : data.node;
                setLiveAgentStatus(nodeStr);
              } else if (data.event === 'token') {
                setLiveAgentStatus(null);
                setMessages(prev => prev.map(m => m.id === aiMessageId ? { ...m, content: m.content + data.content } : m));
              } else if (data.event === 'clear') {
                setMessages(prev => prev.map(m => m.id === aiMessageId ? { ...m, content: '' } : m));
              } else if (data.event === 'end') {
                if (data.session_id) {
                    setSessionId(data.session_id);
                }
                setLiveAgentStatus(null);
              }
            } catch (e) {
                console.error("Error parsing SSE JSON:", e, line);
            }
          }
        }
      }
    } catch (err: any) {
      console.error("Chat error", err);
      // Detect CORS or network errors (fetch throws TypeError on CORS block)
      let errorMessage = "An unexpected error occurred. Please try again.";
      if (err instanceof TypeError && err.message?.includes('fetch')) {
        errorMessage = "⚠️ Could not connect to the server. This may be a CORS or network issue. Please ensure the backend is running and accessible.";
      } else if (err?.message?.includes('HTTP error')) {
        errorMessage = `⚠️ Server returned an error: ${err.message}. Check the backend logs for details.`;
      }
      setMessages(prev => prev.map(m => m.id === aiMessageId ? { ...m, content: errorMessage } : m));
    } finally {
      setLoading(false);
      setLiveAgentStatus(null);
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
        <div className="w-full h-full relative z-10 flex">
          {/* Main Chat Area */}
          <div className="flex-1 h-full relative flex justify-center">
            
            {/* Full width scroll area with scrollbar on the right */}
            <div className="w-full h-full overflow-y-auto flex justify-center">
          
          {/* Centered Chat Content (wider now) */}
          <div className="w-full max-w-[1200px] px-4 md:px-8 pt-8 flex flex-col gap-8 min-h-full">
            
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
                      <img alt="NYRA Logo" className="w-full h-full object-cover rounded-full" src="/nyra_logo.jpg" />
                    </div>
                    <span className="font-display text-sm font-bold gradient-text">NYRA</span>
                  </div>
                  
                  <div className="max-w-[100%] text-on-surface space-y-6">
                    <div className="prose prose-invert prose-p:leading-relaxed prose-pre:bg-surface-container-high prose-pre:border prose-pre:border-outline-variant/30 max-w-none font-body text-lg">
                      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                    
                    {/* RAG Confidence and Sources have been removed based on user preference for a magical UI */}
                    
                    <div className="flex justify-end pt-2">
                      <button
                        onClick={() => handleOptIn(msg.id, msg.content)}
                        disabled={optedInIds.has(msg.id)}
                        className={`hover-lock flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-label text-xs font-semibold transition-all ${
                          optedInIds.has(msg.id) 
                            ? 'bg-tertiary/20 border-tertiary/40 text-tertiary cursor-default' 
                            : 'bg-surface-container-low border-outline-variant/20 text-on-surface-variant hover:text-on-surface hover:border-outline-variant/40'
                        }`}
                        title="Add this Q&A to the shared knowledge base"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                        <span>{optedInIds.has(msg.id) ? 'Added to Shared FAQ' : 'Helpful? Add to Shared FAQ'}</span>
                      </button>
                    </div>
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
            
            <div className="h-56 w-full shrink-0" ref={messagesEndRef} />
          </div>
        </div>
        
        {/* Composer (Floating Glass Container) aligned with chat content */}
        <div className="absolute bottom-8 w-full max-w-[1200px] px-4 md:px-8 z-20">
          <div className="glass-advanced holographic-border rounded-2xl p-2 flex flex-col gap-2">
            <div className="noise-overlay rounded-2xl"></div>
            
            {/* Context Chips Area & Scope Selector */}
            <div className="px-3 pt-2 pb-1 flex justify-between items-center relative">
              <div className="flex items-center gap-2">
                
                {/* Document Selector */}
                <div className="relative">
                  <button 
                    onClick={() => { setIsDropdownOpen(!isDropdownOpen); setIsThinkingDropdownOpen(false); }}
                    className="hover-lock flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-low border border-outline-variant/20 font-label text-xs font-semibold text-on-surface-variant hover:text-on-surface hover:border-outline-variant/40 transition-all">
                    <FolderOpen className="w-4 h-4" />
                    <span className="max-w-[150px] truncate">
                      {selectedDocumentId === 'all' ? 'All Documents' : documents.find(d => d.id === selectedDocumentId)?.filename || 'Document'}
                    </span>
                    <ChevronDown className="w-4 h-4" />
                  </button>

                  {isDropdownOpen && (
                    <div className="absolute bottom-full left-0 mb-2 bg-surface-container-high border border-outline-variant/30 rounded-lg shadow-xl overflow-hidden z-50 min-w-[200px] max-h-48 overflow-y-auto">
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

                {/* Thinking Level Selector */}
                <div className="relative">
                  <button 
                    onClick={() => { setIsThinkingDropdownOpen(!isThinkingDropdownOpen); setIsDropdownOpen(false); }}
                    className="hover-lock flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-low border border-outline-variant/20 font-label text-xs font-semibold text-on-surface-variant hover:text-on-surface hover:border-outline-variant/40 transition-all"
                    title="Select NYRA's Thinking Level"
                  >
                    {thinkingLevel === 'low' ? <Zap className="w-4 h-4 text-amber-400" /> : thinkingLevel === 'medium' ? <Brain className="w-4 h-4 text-primary" /> : <BrainCircuit className="w-4 h-4 text-emerald-400" />}
                    <span className="capitalize">{thinkingLevel}</span>
                    <ChevronDown className="w-4 h-4" />
                  </button>

                  {isThinkingDropdownOpen && (
                    <div className="absolute bottom-full left-0 mb-2 bg-surface-container-high border border-outline-variant/30 rounded-lg shadow-xl overflow-hidden z-50 w-56">
                      <button 
                        onClick={() => { setThinkingLevel('low'); setIsThinkingDropdownOpen(false); }}
                        className={`w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-primary/10 transition-colors ${thinkingLevel === 'low' ? 'bg-primary/5' : ''}`}
                      >
                        <Zap className="w-4 h-4 mt-0.5 text-amber-400 shrink-0" />
                        <div>
                          <p className={`text-xs font-bold ${thinkingLevel === 'low' ? 'text-primary' : 'text-on-surface'}`}>Low / Fast</p>
                          <p className="text-[10px] text-on-surface-variant leading-tight mt-1">Quickest responses, bypasses deep reasoning to save tokens.</p>
                        </div>
                      </button>
                      <button 
                        onClick={() => { setThinkingLevel('medium'); setIsThinkingDropdownOpen(false); }}
                        className={`w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-primary/10 transition-colors border-t border-outline-variant/20 ${thinkingLevel === 'medium' ? 'bg-primary/5' : ''}`}
                      >
                        <Brain className="w-4 h-4 mt-0.5 text-primary shrink-0" />
                        <div>
                          <p className={`text-xs font-bold ${thinkingLevel === 'medium' ? 'text-primary' : 'text-on-surface'}`}>Medium</p>
                          <p className="text-[10px] text-on-surface-variant leading-tight mt-1">Balanced. Uses multi-agent graph with one verification pass.</p>
                        </div>
                      </button>
                      <button 
                        onClick={() => { setThinkingLevel('high'); setIsThinkingDropdownOpen(false); }}
                        className={`w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-primary/10 transition-colors border-t border-outline-variant/20 ${thinkingLevel === 'high' ? 'bg-primary/5' : ''}`}
                      >
                        <BrainCircuit className="w-4 h-4 mt-0.5 text-emerald-400 shrink-0" />
                        <div>
                          <p className={`text-xs font-bold ${thinkingLevel === 'high' ? 'text-primary' : 'text-on-surface'}`}>High / Deep</p>
                          <p className="text-[10px] text-on-surface-variant leading-tight mt-1">Deep reasoning. Will loop up to 3 times to ensure no hallucinations.</p>
                        </div>
                      </button>
                    </div>
                  )}
                </div>

                {/* Coach Toggle */}
                <button 
                  onClick={() => setShowCoach(!showCoach)}
                  className={`hover-lock flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-label text-xs font-semibold transition-all ${showCoach ? 'bg-tertiary/20 border-tertiary/40 text-tertiary' : 'bg-surface-container-low border-outline-variant/20 text-on-surface-variant hover:text-on-surface hover:border-outline-variant/40'}`}
                  title="Toggle Prompt Coach"
                >
                  <Lightbulb className="w-4 h-4" />
                  <span className="hidden sm:inline">Coach</span>
                </button>

              </div>
            </div>
            
            <div className="flex items-end gap-2 px-2 pb-1">
              <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                onChange={handleFileUpload} 
                accept=".pdf,.txt,.docx,.jpg,.jpeg,.png,.webp,.mp3,.wav,.m4a"
              />
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="hover-lock w-10 h-10 rounded-xl hover:bg-surface-container transition-colors flex items-center justify-center text-on-surface-variant hover:text-primary shrink-0"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              
              <div className={`flex-1 min-h-[44px] bg-transparent flex items-center rounded-xl transition-all ${isListening ? 'ring-2 ring-tertiary/50 bg-tertiary/5' : ''}`}>
                <textarea 
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-transparent border-none text-on-surface placeholder-on-surface-variant resize-none focus:ring-0 max-h-32 overflow-y-auto font-body text-base py-3 px-2 outline-none" 
                  placeholder={isListening ? "Listening..." : "Message NYRA..."} 
                  rows={1}
                />
              </div>
              
              {sttSupported && (
                <button 
                  onClick={handleToggleMic}
                  className={`hover-lock w-10 h-10 rounded-xl flex items-center justify-center transition-all shrink-0 mb-1 ${isListening ? 'bg-tertiary/20 text-tertiary animate-pulse shadow-[0_0_15px_rgba(var(--color-tertiary),0.3)]' : 'hover:bg-surface-container text-on-surface-variant hover:text-tertiary'}`}>
                  <Mic className="w-5 h-5" />
                </button>
              )}

              <button 
                onClick={handleSend}
                disabled={!input.trim() || loading || isListening}
                className="hover-lock w-10 h-10 rounded-xl bg-primary text-on-primary flex items-center justify-center hover:bg-primary-container transition-colors shrink-0 mb-1 disabled:opacity-50 disabled:cursor-not-allowed">
                <ArrowUp className="w-5 h-5" />
              </button>
            </div>
          </div>
          <div className="text-center mt-3 text-[10px] text-on-surface-variant/60 font-medium tracking-wide">
            NYRA strives for accuracy, but may occasionally make mistakes. Please verify important information.
          </div>
        </div>
        </div>

        {/* Coach Sidebar */}
        {showCoach && (
          <div className="hidden lg:block shrink-0 h-full">
            <PromptCoach 
              sessionId={sessionId} 
              lastUserMessage={messages.filter(m => m.role === 'user').pop()?.content} 
            />
          </div>
        )}
        </div>
        
        {isOrbOpen && (
          <CinematicVoiceOrb 
            onClose={() => setIsOrbOpen(false)}
            sessionId={sessionId}
            onMessageTranscribed={(msg, response, newSessionId) => {
              const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: msg };
              const aiMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'ai', content: response };
              setMessages(prev => [...prev, userMsg, aiMsg]);
              if (newSessionId && !sessionId) {
                setSessionId(newSessionId.toString());
              }
            }}
          />
        )}
      </ChatLayout>
    );
  };
  
  export default Chat;
