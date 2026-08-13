import React, { useState, useEffect } from 'react';
import { Volume2, Square, Mic, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Voice: React.FC = () => {
  const navigate = useNavigate();
  const [state, setState] = useState<'listening' | 'processing' | 'speaking'>('processing');
  const [selectedPersona, setSelectedPersona] = useState('Atlas');

  useEffect(() => {
    const interval = setInterval(() => {
      setState((prev) => {
        if (prev === 'listening') return 'processing';
        if (prev === 'processing') return 'speaking';
        return 'listening';
      });
    }, 4000);
    return () => clearInterval(interval);
  }, []);



  const personas = [
    { id: 'A', name: 'Atlas', desc: 'Authoritative, Calm', gradient: 'from-primary to-secondary-container' },
    { id: 'L', name: 'Lyra', desc: 'Empathetic, Warm', gradient: 'from-secondary to-tertiary-container' },
    { id: 'N', name: 'Nova', desc: 'Energetic, Bright', gradient: 'from-tertiary to-primary-container' },
    { id: 'H', name: 'Helios', desc: 'Direct, Professional', gradient: 'from-error to-error-container' },
    { id: 'E', name: 'Eris', desc: 'Inquisitive, Sharp', gradient: 'from-primary-fixed to-secondary-fixed' },
  ];

  return (
    <div className="bg-background text-on-surface h-screen w-screen overflow-hidden font-body relative flex flex-col items-center justify-center dark">
      {/* Ambient Background Layers */}
      <div className="ambient-glow"></div>
      <div className="absolute inset-0 bg-gradient-to-b from-surface-dim via-background to-surface-container-lowest opacity-90 z-0"></div>
      
      {/* AI Waveform Visualization */}
      <div className={`absolute top-0 left-0 w-full h-1/2 overflow-hidden z-10 mix-blend-screen transition-all duration-1000 ${state === 'listening' ? 'opacity-30' : state === 'processing' ? 'opacity-70' : 'opacity-90'}`}>
        <div 
          className={`w-full h-full bg-cover bg-bottom ${state === 'listening' ? 'wave-anim-calm' : 'wave-anim-dynamic'}`}
          style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDbUXwpBBpwTWnrVV9PzCeD8N0F99xbc1V9XwvApHm65dSIwW-9zvUBCSPbSWjc4icu-v4VqLFtI8Got9kP8f7Q2slVoOTT49Fns4RKf3dMYTdEo4OEIzPqmj4sIzUya75DdCpNKTcKvT3d8JGS1k19-0rmNr4MYrGvVE0O-gmtp1Rw8WAg-WahhJRvhA2S4L-yry4qYn7CFRz8etPhJVZJbYQZfweoB0dgipFyxlRp2HsmFkzdPszUhg')" }}
        ></div>
      </div>
      
      {/* User Waveform Visualization */}
      <div className={`absolute bottom-0 left-0 w-full h-1/2 overflow-hidden z-10 mix-blend-screen transition-all duration-1000 ${state === 'listening' ? 'opacity-80' : state === 'processing' ? 'opacity-30' : 'opacity-20'}`}>
        <div 
          className="w-full h-full bg-cover bg-top mesh-anim-reactive"
          style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuAv2XTC5DNwquETxnVqtGB9MNsQxg4UBh0rdgHG09Wo_e4_pfrwNi5rd0sujO4X5x9Bn38PdkXLHV0NTnXNDTTDyleXjjpj-XuVec2GlyYuJ1fzKEzaBDX-s4NUCYhVTWb_s11t8oDdRoTer-nAdladv_4ZzD8m3nfFAUSLadcdO6YFyuV_UCpHCJwASDzRlhplRVfmq05cZv6ejAccCacBnTJLgF-n_jX0xK0YnklvVrkSt4ge_Q7ahw')" }}
        ></div>
      </div>
      
      {/* Left Sidebar: Persona Selection */}
      <div className="absolute left-6 top-1/2 -translate-y-1/2 z-30 w-64 hidden lg:flex flex-col gap-4">
        <h3 className="font-display text-sm font-bold text-primary uppercase tracking-widest px-2 mb-2">Voice Personas</h3>
        <div className="flex flex-col gap-3">
          {personas.map(p => (
            <button 
              key={p.name}
              onClick={() => setSelectedPersona(p.name)}
              className={`persona-card relative w-full p-4 rounded-xl flex items-center gap-4 text-left group ${selectedPersona === p.name ? 'selected' : ''}`}
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${selectedPersona === p.name ? `bg-gradient-to-br ${p.gradient} text-on-primary` : 'bg-surface-container-high border border-outline-variant/30 text-primary'}`}>
                {p.id}
              </div>
              <div>
                <h4 className="font-bold text-on-surface">{p.name}</h4>
                <p className="text-xs font-label text-on-surface-variant">{p.desc}</p>
              </div>
            </button>
          ))}
        </div>
        <button className="mt-4 w-full p-3 rounded-xl border border-dashed border-primary/40 text-primary hover:bg-primary/10 hover:border-primary transition-all flex items-center justify-center gap-2 text-sm font-semibold">
          <Plus className="w-5 h-5" />
          Clone New Voice
        </button>
      </div>
      
      {/* Top Transcript Bar */}
      <div className="absolute top-16 left-1/2 -translate-x-1/2 z-30 w-11/12 max-w-2xl">
        <div className="glass-panel rounded-xl p-4 flex flex-col items-center justify-center text-center shadow-lg transition-all duration-300">
          <p className="font-label text-xs font-bold text-primary uppercase tracking-widest mb-2">{state}</p>
          <p className="font-display text-2xl md:text-3xl text-on-surface font-light leading-snug">
            {state === 'speaking' ? '"Analyzing global market trends for Q3..."' : state === 'processing' ? '"Thinking..."' : '"I am listening..."'}
          </p>
        </div>
      </div>
      
      {/* Central State Label */}
      <div className="relative z-20 flex flex-col items-center justify-center mt-8">
        <p className="mt-8 font-label text-xs font-bold text-on-surface-variant tracking-widest uppercase">{state}</p>
      </div>
      
      {/* Bottom Control Bar */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-30">
        <div className="glass-panel-elevated rounded-full px-8 py-4 flex items-center gap-8">
          <button className="w-12 h-12 rounded-full flex items-center justify-center text-on-surface-variant hover:text-primary hover:bg-surface-container transition-all duration-300">
            <Volume2 className="w-6 h-6" />
          </button>
          <button onClick={() => navigate('/chat')} className="relative w-14 h-14 rounded-full bg-gradient-to-b from-error to-error-container shadow-[0_0_20px_rgba(255,180,171,0.4)] flex items-center justify-center group active:scale-90 transition-all duration-300">
            <div className="absolute inset-0 rounded-full bg-error opacity-20 blur-md group-hover:opacity-40 transition-opacity"></div>
            <Square className="text-on-error w-6 h-6 relative z-10 fill-current" />
          </button>
          <button className="w-12 h-12 rounded-full flex items-center justify-center text-primary bg-primary-container/20 border border-primary/30 hover:bg-primary-container/40 transition-all duration-300">
            <Mic className="w-6 h-6" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Voice;
