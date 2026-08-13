import React, { useState, useRef, useEffect } from 'react';
import ChatLayout from './layout/ChatLayout';
import { UploadCloud, FileText, BookOpen, Layers, Database, Folder, CheckCircle, Eye, Trash2, AlertCircle, RefreshCw } from 'lucide-react';
import TiltCard from './common/TiltCard';
import api from '../api/client';

const KnowledgeBase: React.FC = () => {
  const [documents, setDocuments] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = async () => {
    try {
      const res = await api.get('/api/documents/');
      setDocuments(res.data);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    }
  };

  useEffect(() => {
    fetchDocuments();
    // Poll for document status updates every 5 seconds
    const interval = setInterval(fetchDocuments, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post('/api/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      fetchDocuments(); // refresh list
    } catch (err) {
      console.error("Upload failed", err);
      alert("Failed to upload document");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (e: React.MouseEvent, docId: number) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await api.delete(`/api/documents/${docId}`);
      fetchDocuments();
    } catch (err) {
      console.error("Delete failed", err);
      alert("Failed to delete document");
    }
  };

  return (
    <ChatLayout>
      <div className="w-full h-full overflow-y-auto px-4 md:px-8 pb-20 scrollbar-hide pt-8">
        <div className="max-w-[1200px] mx-auto flex flex-col gap-10">
          
          {/* Page Header */}
          <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 animate-sweep">
            <div>
              <h2 className="text-3xl md:text-5xl font-display font-bold gradient-text">Knowledge Base</h2>
              <p className="text-lg font-body text-on-surface-variant mt-2 max-w-xl">
                Your personal document management workspace. Upload, organize, and let NYRA synthesize your data.
              </p>
            </div>
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              onChange={handleFileChange} 
              accept=".pdf,.txt,.docx"
            />
            <button 
              onClick={handleUploadClick}
              disabled={uploading}
              className="px-6 py-3 rounded-full bg-gradient-to-r from-primary to-inverse-primary text-on-primary font-label text-sm font-bold flex items-center gap-2 ambient-glow hover:shadow-[0_0_20px_rgba(192,193,255,0.4)] transition-all duration-300 transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed">
              <UploadCloud className="w-5 h-5" />
              {uploading ? 'Uploading...' : 'Upload Document'}
            </button>
          </header>

          {/* Analytics Panel */}
          <section className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full animate-sweep delay-100">
            <TiltCard>
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-1 transform-style-preserve-3d h-full">
                <span className="text-on-surface-variant font-label text-xs flex items-center gap-2 uppercase tracking-wider" style={{ transform: "translateZ(15px)" }}>
                  <FileText className="w-4 h-4 text-tertiary" /> Total Documents
                </span>
                <span className="text-3xl font-display font-bold text-on-surface mt-2" style={{ transform: "translateZ(30px)" }}>{documents.length}</span>
              </div>
            </TiltCard>
            <TiltCard>
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-1 transform-style-preserve-3d h-full">
                <span className="text-on-surface-variant font-label text-xs flex items-center gap-2 uppercase tracking-wider" style={{ transform: "translateZ(15px)" }}>
                  <CheckCircle className="w-4 h-4 text-tertiary" /> Ready Documents
                </span>
                <span className="text-3xl font-display font-bold text-on-surface mt-2" style={{ transform: "translateZ(30px)" }}>{documents.filter(d => d.status === 'ready').length}</span>
              </div>
            </TiltCard>
            <TiltCard>
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-1 transform-style-preserve-3d h-full">
                <span className="text-on-surface-variant font-label text-xs flex items-center gap-2 uppercase tracking-wider" style={{ transform: "translateZ(15px)" }}>
                  <AlertCircle className="w-4 h-4 text-tertiary" /> Failed Documents
                </span>
                <span className="text-3xl font-display font-bold text-on-surface mt-2" style={{ transform: "translateZ(30px)" }}>{documents.filter(d => d.status === 'failed').length}</span>
              </div>
            </TiltCard>
            <TiltCard>
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-1 transform-style-preserve-3d h-full">
                <span className="text-on-surface-variant font-label text-xs flex items-center gap-2 uppercase tracking-wider" style={{ transform: "translateZ(15px)" }}>
                  <Database className="w-4 h-4 text-tertiary" /> Indexing Status
                </span>
                <div className="flex items-center gap-2 mt-4" style={{ transform: "translateZ(20px)" }}>
                  <div className="flex-1 h-2 bg-surface-variant rounded-full overflow-hidden">
                    <div className="h-full bg-tertiary rounded-full" style={{ width: `${documents.length > 0 ? Math.round((documents.filter(d => d.status === 'ready').length / documents.length) * 100) : 0}%` }}></div>
                  </div>
                  <span className="text-tertiary font-label text-xs font-bold">{documents.length > 0 ? Math.round((documents.filter(d => d.status === 'ready').length / documents.length) * 100) : 0}%</span>
                </div>
              </div>
            </TiltCard>
          </section>

          {/* Dropzone */}
          <section onClick={handleUploadClick} className="w-full h-48 rounded-xl glass-dropzone flex flex-col items-center justify-center cursor-pointer group animate-sweep delay-200">
            <div className="w-16 h-16 rounded-full bg-surface-variant/50 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <UploadCloud className="w-8 h-8 text-primary opacity-80 group-hover:opacity-100" />
            </div>
            <p className="text-lg font-body text-on-surface-variant group-hover:text-primary transition-colors">
              {uploading ? 'Uploading your document...' : (
                <>Drop your documents here or <span className="text-primary underline underline-offset-4">browse</span></>
              )}
            </p>
            <p className="font-label text-xs text-outline mt-2">Supports PDF, DOCX, TXT up to 50MB</p>
          </section>

          {/* Document Collections */}
          <div className="flex flex-col gap-8 animate-sweep delay-300">
            
            <section>
              <h3 className="text-2xl font-display font-semibold text-on-surface mb-4 flex items-center gap-2">
                <Folder className="text-primary w-6 h-6" /> All Documents
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {documents.map((doc, index) => (
                  <TiltCard key={doc.id || index}>
                    <div className={`glass-panel rounded-xl p-5 flex flex-col gap-4 glass-panel-hover group relative overflow-hidden transition-all duration-300 transform-style-preserve-3d h-full ${doc.status === 'failed' ? 'border-error/20' : ''}`}>
                    {doc.status === 'processing' && (
                      <div className="absolute inset-0 shimmer-effect opacity-30 pointer-events-none"></div>
                    )}
                    {doc.status === 'failed' && (
                      <div className="absolute top-0 right-0 w-1 h-full bg-error/50"></div>
                    )}
                    
                    <div className="flex items-start gap-4 relative z-10" style={{ transform: "translateZ(20px)" }}>
                      <div className={`w-12 h-12 rounded-lg ${doc.status === 'failed' ? 'bg-error/10 border-error/20' : 'bg-surface-variant/50 border-outline-variant/30'} flex items-center justify-center flex-shrink-0 border`}>
                        {doc.status === 'processing' ? (
                          <RefreshCw className="text-primary w-6 h-6 animate-spin" />
                        ) : doc.status === 'failed' ? (
                          <AlertCircle className="text-error w-6 h-6" />
                        ) : (
                          <FileText className="text-tertiary w-6 h-6" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-body font-semibold text-on-surface truncate">{doc.filename}</h3>
                        <p className="font-label text-xs text-on-surface-variant mt-1 capitalize">{doc.status}</p>
                      </div>
                    </div>
                    
                    {/* Document Health Status */}
                    <div className="flex gap-1 mt-1 relative z-10">
                      <div className={`h-1 flex-1 rounded-full ${doc.status === 'failed' ? 'bg-error' : 'bg-tertiary'}`}></div>
                      <div className={`h-1 flex-1 rounded-full ${doc.status === 'uploaded' || doc.status === 'failed' ? 'bg-surface-variant' : 'bg-tertiary'}`}></div>
                      <div className={`h-1 flex-1 rounded-full ${doc.status === 'processing' ? 'bg-primary animate-pulse' : doc.status === 'ready' ? 'bg-tertiary' : 'bg-surface-variant'}`}></div>
                      <div className={`h-1 flex-1 rounded-full ${doc.status === 'ready' ? 'bg-tertiary' : 'bg-surface-variant'}`}></div>
                    </div>
                    
                    <div className="flex items-center justify-between mt-2 pt-4 border-t border-white/5 relative z-10">
                      {doc.status === 'ready' && (
                        <span className="inline-flex items-center gap-1.5 text-tertiary font-label text-xs font-semibold bg-tertiary/10 px-2 py-1 rounded-md">
                          <CheckCircle className="w-4 h-4" /> Ready for Chat
                        </span>
                      )}
                      {doc.status === 'processing' && (
                        <span className="inline-flex items-center gap-1.5 text-primary font-label text-xs font-semibold px-2 py-1">
                           Processing Vectors...
                        </span>
                      )}
                      {doc.status === 'failed' && (
                        <span className="inline-flex items-center gap-1.5 text-error font-label text-xs font-semibold px-2 py-1">
                           Failed
                        </span>
                      )}
                      
                      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity translate-y-2 group-hover:translate-y-0 duration-200">
                        <button 
                          onClick={(e) => handleDelete(e, doc.id)}
                          className="w-8 h-8 rounded-full bg-surface-variant/50 hover:bg-error/20 hover:text-error flex items-center justify-center transition-colors text-on-surface-variant">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                  </TiltCard>
                ))}
              </div>
            </section>
          </div>

        </div>
      </div>
    </ChatLayout>
  );
};

export default KnowledgeBase;
