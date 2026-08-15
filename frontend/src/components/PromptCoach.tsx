import React, { useEffect, useState } from 'react';
import { BarChart, Bar, Tooltip, ResponsiveContainer } from 'recharts';
import { Lightbulb, Info } from 'lucide-react';
import api from '../api/client';

interface PromptCoachProps {
  sessionId?: string;
  lastUserMessage?: string;
}

export const PromptCoach: React.FC<PromptCoachProps> = ({ sessionId, lastUserMessage }) => {
  const [stats, setStats] = useState<any>(null);
  const [tip, setTip] = useState<string>('');

  useEffect(() => {
    if (sessionId) {
      api.get(`/api/analytics/session/${sessionId}`)
        .then(res => setStats(res.data))
        .catch(err => console.error("Failed to load analytics", err));
    }
  }, [sessionId, lastUserMessage]);

  useEffect(() => {
    if (lastUserMessage) {
      api.post('/api/analytics/prompt-quality', { message: lastUserMessage })
        .then(res => setTip(res.data.tip))
        .catch(err => console.error("Failed to get tip", err));
    }
  }, [lastUserMessage]);

  if (!stats) return null;

  return (
    <div className="w-80 h-full bg-surface-container/30 backdrop-blur-md border-l border-white/5 p-4 flex flex-col gap-6 animate-sweep overflow-y-auto">
      <div>
        <h3 className="text-lg font-display font-semibold text-on-surface flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-tertiary" /> Prompt Coach
        </h3>
        <p className="text-xs font-body text-on-surface-variant mt-1">
          Simple insights to help you get better answers.
        </p>
      </div>

      {tip && (
        <div className="bg-tertiary/10 border border-tertiary/20 rounded-xl p-3">
          <p className="text-sm font-body text-tertiary flex items-start gap-2">
            <Info className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{tip}</span>
          </p>
        </div>
      )}

      <div className="flex flex-col gap-3">
        <h4 className="text-sm font-label text-on-surface uppercase tracking-wider">Session Stats</h4>
        
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-surface/50 rounded-lg p-2 text-center border border-white/5">
            <div className="text-xl font-display text-on-surface">{stats.message_count}</div>
            <div className="text-[10px] uppercase font-label text-on-surface-variant">Messages</div>
          </div>
          <div className="bg-surface/50 rounded-lg p-2 text-center border border-white/5">
            <div className="text-xl font-display text-on-surface">{stats.avg_length}</div>
            <div className="text-[10px] uppercase font-label text-on-surface-variant">Avg Chars</div>
          </div>
          <div className="bg-surface/50 rounded-lg p-2 text-center border border-white/5">
            <div className="text-xl font-display text-primary">{Math.round(stats.specific_ratio * 100)}%</div>
            <div className="text-[10px] uppercase font-label text-on-surface-variant">Specific</div>
          </div>
          <div className="bg-surface/50 rounded-lg p-2 text-center border border-white/5">
            <div className="text-xl font-display text-error">{Math.round(stats.vague_ratio * 100)}%</div>
            <div className="text-[10px] uppercase font-label text-on-surface-variant">Vague</div>
          </div>
        </div>
      </div>

      {stats.history && stats.history.length > 0 && (
        <div className="flex-1 min-h-[150px]">
          <h4 className="text-sm font-label text-on-surface uppercase tracking-wider mb-2">Length over time</h4>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats.history}>
              <Tooltip 
                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                contentStyle={{ backgroundColor: '#1E1E2E', border: 'none', borderRadius: '8px', color: '#fff' }}
              />
              <Bar 
                dataKey="length" 
                fill="#C0C1FF" 
                radius={[4, 4, 0, 0]} 
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};
