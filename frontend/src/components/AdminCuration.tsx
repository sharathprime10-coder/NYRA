import React, { useEffect, useState } from 'react';
import { Database, Check, X, ShieldAlert, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface StagingPair {
  id: string;
  user_query: string;
  ai_response: string;
  status: string;
  created_at: string;
}

const AdminCuration: React.FC = () => {
  const [pairs, setPairs] = useState<StagingPair[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPairs = async () => {
    try {
      const res = await api.get('/api/curation/pending');
      setPairs(res.data);
    } catch (err) {
      console.error("Failed to fetch pairs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPairs();
  }, []);

  const handleApprove = async (id: string) => {
    try {
      await api.post(`/api/curation/approve/${id}`);
      setPairs(pairs.filter(p => p.id !== id));
      toast.success("Pair approved and added to Knowledge Base");
    } catch (err) {
      console.error("Failed to approve", err);
      toast.error("Failed to approve pair");
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.post(`/api/curation/reject/${id}`);
      setPairs(pairs.filter(p => p.id !== id));
      toast.success("Pair rejected and removed");
    } catch (err) {
      console.error("Failed to reject", err);
      toast.error("Failed to reject pair");
    }
  };

  return (
    <div className="min-h-screen bg-background p-8 flex flex-col items-center overflow-y-auto">
      <div className="w-full max-w-4xl flex flex-col gap-8">
        <header className="flex items-center gap-3 border-b border-outline-variant/30 pb-4">
          <div className="w-10 h-10 rounded-xl bg-error/10 border border-error/30 flex items-center justify-center text-error">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-2xl font-display font-bold text-on-surface">Knowledge Curation</h1>
            <p className="text-sm font-body text-on-surface-variant">Admin review for opted-in user Q&A pairs.</p>
          </div>
        </header>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-10 opacity-50">
            <Loader2 className="w-8 h-8 animate-spin mb-4 text-primary" />
            <p className="text-sm font-label uppercase tracking-widest">Loading queue...</p>
          </div>
        ) : pairs.length === 0 ? (
          <div className="text-center p-12 bg-surface-container-low rounded-2xl border border-outline-variant/20">
            <Database className="w-12 h-12 text-tertiary mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-display text-on-surface">No Pending Pairs</h3>
            <p className="text-sm text-on-surface-variant mt-2">All caught up! Wait for users to opt-in more knowledge.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {pairs.map((pair) => (
              <div key={pair.id} className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-6 flex flex-col gap-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h4 className="text-xs font-label text-primary uppercase tracking-wider mb-2">User Query</h4>
                    <p className="text-on-surface font-body mb-4 bg-surface-container-high p-3 rounded-xl border border-white/5">{pair.user_query}</p>
                    
                    <h4 className="text-xs font-label text-tertiary uppercase tracking-wider mb-2">AI Response</h4>
                    <div className="text-on-surface font-body bg-surface-container-high p-4 rounded-xl border border-white/5 prose prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{pair.ai_response}</ReactMarkdown>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-3 mt-2 pt-4 border-t border-outline-variant/20">
                  <button 
                    onClick={() => handleReject(pair.id)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-error/10 text-error hover:bg-error/20 transition-colors font-label text-sm"
                  >
                    <X className="w-4 h-4" /> Reject (Discard)
                  </button>
                  <button 
                    onClick={() => handleApprove(pair.id)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors font-label text-sm border border-emerald-500/20"
                  >
                    <Check className="w-4 h-4" /> Approve (Add to Shared FAQ)
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminCuration;
