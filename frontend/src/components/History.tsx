import React, { useEffect, useState } from 'react';
import ChatLayout from './layout/ChatLayout';
import { History as HistoryIcon, MessageSquare, Clock, ChevronRight } from 'lucide-react';
import api from '../api/client';
import { useNavigate } from 'react-router-dom';

interface ChatSession {
  id: number;
  title: string;
  created_at: string;
}

const History: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/api/chat/history')
      .then(res => {
        setSessions(res.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <ChatLayout>
      <div className="w-full h-full flex flex-col p-8 md:p-12 animate-sweep">
        <div className="flex items-center gap-4 mb-8">
          <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center">
            <HistoryIcon className="w-6 h-6 text-primary" />
          </div>
          <h2 className="text-3xl font-display font-bold text-on-surface">Chat History</h2>
        </div>

        {loading ? (
          <div className="flex justify-center items-center flex-1">
            <div className="animate-pulse flex flex-col items-center">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className="text-on-surface-variant">Loading history...</p>
            </div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center opacity-50">
            <h3 className="font-display text-xl mb-2 text-on-surface">No conversations yet</h3>
            <p className="font-body text-sm text-on-surface-variant max-w-sm">Start chatting with NYRA and your history will appear here.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-max overflow-y-auto pb-20 scrollbar-hide">
            {sessions.map(session => (
              <div 
                key={session.id}
                onClick={() => navigate(`/chat/${session.id}`)}
                className="glass-card hover-lock p-6 rounded-2xl cursor-pointer group flex flex-col gap-4 border border-outline-variant/30 hover:border-primary/50 transition-all"
              >
                <div className="flex justify-between items-start">
                  <div className="p-3 rounded-xl bg-surface-container-high group-hover:bg-primary/20 transition-colors">
                    <MessageSquare className="w-5 h-5 text-tertiary group-hover:text-primary transition-colors" />
                  </div>
                  <div className="w-8 h-8 rounded-full flex items-center justify-center bg-transparent group-hover:bg-surface-container transition-colors">
                    <ChevronRight className="w-4 h-4 text-on-surface-variant group-hover:text-primary" />
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-display font-bold text-on-surface mb-1 truncate">{session.title}</h3>
                  <div className="flex items-center gap-1.5 text-xs font-label text-on-surface-variant">
                    <Clock className="w-3 h-3" />
                    {new Date(session.created_at).toLocaleDateString(undefined, { 
                      year: 'numeric', month: 'short', day: 'numeric', 
                      hour: '2-digit', minute: '2-digit' 
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </ChatLayout>
  );
};

export default History;
