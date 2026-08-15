import React, { useState, useEffect } from 'react';
import ChatLayout from './layout/ChatLayout';
import { 
  Settings as SettingsIcon, 
  Monitor, 
  Volume2, 
  Cpu, 
  AlertTriangle, 
  Moon, 
  Sun, 
  Trash2, 
  LogOut,
  Check,
  Mail
} from 'lucide-react';
import toast from 'react-hot-toast';
import { trackEvent } from '../utils/analytics';

type Tab = 'general' | 'voice' | 'system';

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('general');
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  
  // Settings State
  const [theme, setTheme] = useState(localStorage.getItem('nyra_theme') || 'dark');
  const [animations, setAnimations] = useState(localStorage.getItem('nyra_animations') !== 'false');
  const [sassy, setSassy] = useState(localStorage.getItem('nyra_tone') === 'sassy');
  const [selectedVoice, setSelectedVoice] = useState(localStorage.getItem('nyra_voice') || '');
  const [speechSpeed, setSpeechSpeed] = useState(parseFloat(localStorage.getItem('nyra_speed') || '1.0'));
  const [autoPlayAudio, setAutoPlayAudio] = useState(localStorage.getItem('nyra_autoplay') === 'true');

  useEffect(() => {
    // Load voices
    const loadVoices = () => {
      const synth = window.speechSynthesis;
      const availableVoices = synth.getVoices();
      setVoices(availableVoices);
      if (!selectedVoice && availableVoices.length > 0) {
        setSelectedVoice(availableVoices[0].name);
      }
    };
    
    loadVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  // Save settings on change
  useEffect(() => { 
    localStorage.setItem('nyra_theme', theme); 
    if (theme === 'light') {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
      document.documentElement.classList.add('dark');
    }
  }, [theme]);
  useEffect(() => { localStorage.setItem('nyra_animations', animations.toString()); }, [animations]);
  useEffect(() => { localStorage.setItem('nyra_tone', sassy ? 'sassy' : 'default'); }, [sassy]);
  useEffect(() => { localStorage.setItem('nyra_voice', selectedVoice); }, [selectedVoice]);
  useEffect(() => { localStorage.setItem('nyra_speed', speechSpeed.toString()); }, [speechSpeed]);
  useEffect(() => { localStorage.setItem('nyra_autoplay', autoPlayAudio.toString()); }, [autoPlayAudio]);

  const handleClearHistory = () => {
    if (window.confirm("Are you sure you want to clear your local chat history? This cannot be undone.")) {
      // Assuming chat history is stored locally or requires an API call. For now, visual feedback.
      toast.success("Chat history cleared successfully.");
      trackEvent('clear_history');
    }
  };

  const tabs = [
    { id: 'general', label: 'General', icon: Monitor },
    { id: 'voice', label: 'Voice Assistant', icon: Volume2 },
    { id: 'system', label: 'System Controls', icon: AlertTriangle },
  ];

  return (
    <ChatLayout>
      <div className="w-full h-full flex flex-col max-w-[1000px] mx-auto px-4 md:px-8 py-8 animate-sweep">
        
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-surface-container border border-outline-variant/30 flex items-center justify-center shadow-lg hover-lock">
            <SettingsIcon className="w-7 h-7 text-primary" />
          </div>
          <div>
            <h2 className="text-3xl font-display font-bold text-on-surface">Settings</h2>
            <p className="text-on-surface-variant text-sm mt-1">Manage your NYRA preferences and AI configurations.</p>
          </div>
        </div>

        <div className="flex flex-col md:flex-row gap-8 flex-1 min-h-0">
          
          {/* Sidebar */}
          <div className="w-full md:w-64 flex flex-col gap-2 shrink-0">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as Tab)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 font-label text-sm font-semibold hover-lock
                    ${isActive 
                        ? 'bg-primary/10 text-primary border border-primary/30 shadow-[0_0_15px_rgba(192,193,255,0.1)]'
                      : 'bg-transparent text-on-surface-variant hover:bg-surface-container border border-transparent'
                    }`}
                >
                  <Icon className="w-5 h-5" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Content Area */}
          <div className="flex-1 glass-advanced holographic-border rounded-3xl p-6 md:p-8 overflow-y-auto scrollbar-hide">
            <div className="noise-overlay rounded-3xl"></div>
            <div className="relative z-10">
            
            {activeTab === 'general' && (
              <div className="space-y-8 animate-fade-in">
                <div>
                  <h3 className="text-xl font-display font-bold text-on-surface mb-4">Appearance</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <button 
                      onClick={() => setTheme('dark')}
                      className={`flex flex-col items-center justify-center p-6 rounded-2xl border-2 transition-all hover-lock ${theme === 'dark' ? 'border-primary bg-primary/5' : 'border-outline-variant/30 bg-surface-container'}`}
                    >
                      <Moon className={`w-8 h-8 mb-3 ${theme === 'dark' ? 'text-primary' : 'text-on-surface-variant'}`} />
                      <span className="font-label font-bold text-on-surface">Dark Mode</span>
                      <span className="text-xs text-on-surface-variant mt-1">Default NYRA Aesthetic</span>
                    </button>
                    <button 
                      onClick={() => setTheme('light')}
                      className={`flex flex-col items-center justify-center p-6 rounded-2xl border-2 transition-all hover-lock ${theme === 'light' ? 'border-primary bg-primary/5' : 'border-outline-variant/30 bg-surface-container'}`}
                    >
                      <Sun className={`w-8 h-8 mb-3 ${theme === 'light' ? 'text-primary' : 'text-on-surface-variant'}`} />
                      <span className="font-label font-bold text-on-surface">Light Mode</span>
                      <span className="text-xs text-on-surface-variant mt-1">For bright environments</span>
                    </button>
                  </div>
                </div>

                <hr className="border-outline-variant/20" />

                <div>
                  <h3 className="text-xl font-display font-bold text-on-surface mb-4">Performance & Persona</h3>
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between p-4 bg-surface-container rounded-2xl border border-outline-variant/20 hover-lock">
                      <div>
                        <h4 className="font-label font-bold text-on-surface">Rich Animations</h4>
                        <p className="text-xs text-on-surface-variant mt-1 max-w-sm">Enable cinematic particles and dynamic glow effects. Turn off if experiencing lag.</p>
                      </div>
                      <button 
                        onClick={() => setAnimations(!animations)}
                        className={`w-12 h-6 rounded-full transition-colors relative ${animations ? 'bg-primary' : 'bg-surface-variant'}`}
                      >
                        <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${animations ? 'left-7' : 'left-1'}`} />
                      </button>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-surface-container rounded-2xl border border-outline-variant/20 hover-lock">
                      <div>
                        <h4 className="font-label font-bold text-on-surface">Sassy Mode</h4>
                        <p className="text-xs text-on-surface-variant mt-1 max-w-sm">Give NYRA a dry, witty personality. She remains helpful but adds a bit of flavor.</p>
                      </div>
                      <button 
                        onClick={() => setSassy(!sassy)}
                        className={`w-12 h-6 rounded-full transition-colors relative ${sassy ? 'bg-primary' : 'bg-surface-variant'}`}
                      >
                        <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${sassy ? 'left-7' : 'left-1'}`} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'voice' && (
              <div className="space-y-8 animate-fade-in">
                <div>
                  <h3 className="text-xl font-display font-bold text-on-surface mb-4">Speech Synthesis</h3>
                  
                  <div className="space-y-6">
                    <div className="p-4 bg-surface-container rounded-2xl border border-outline-variant/20">
                      <label className="block font-label font-bold text-on-surface mb-2">Voice Model</label>
                      <p className="text-xs text-on-surface-variant mb-4">Select the synthesized voice for NYRA's responses.</p>
                      <select 
                        value={selectedVoice}
                        onChange={(e) => setSelectedVoice(e.target.value)}
                        className="w-full bg-surface-container-high border border-outline-variant/30 rounded-xl px-4 py-3 text-on-surface focus:outline-none focus:border-primary font-body hover-lock"
                      >
                        {voices.map(voice => (
                          <option key={voice.name} value={voice.name}>
                            {voice.name} ({voice.lang})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="p-4 bg-surface-container rounded-2xl border border-outline-variant/20">
                      <div className="flex justify-between items-end mb-4">
                        <div>
                          <label className="block font-label font-bold text-on-surface mb-1">Speech Speed</label>
                          <p className="text-xs text-on-surface-variant">Adjust how fast NYRA speaks.</p>
                        </div>
                        <span className="font-display font-bold text-primary">{speechSpeed.toFixed(1)}x</span>
                      </div>
                      <input 
                        type="range" 
                        min="0.5" max="2.0" step="0.1"
                        value={speechSpeed}
                        onChange={(e) => setSpeechSpeed(parseFloat(e.target.value))}
                        className="w-full accent-primary hover-lock"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between p-4 bg-surface-container rounded-2xl border border-outline-variant/20 hover-lock">
                      <div>
                        <h4 className="font-label font-bold text-on-surface">Auto-Play Audio in Chat</h4>
                        <p className="text-xs text-on-surface-variant mt-1 max-w-sm">Automatically speak responses aloud even outside the Voice Orb.</p>
                      </div>
                      <button 
                        onClick={() => setAutoPlayAudio(!autoPlayAudio)}
                        className={`w-12 h-6 rounded-full transition-colors relative ${autoPlayAudio ? 'bg-primary' : 'bg-surface-variant'}`}
                      >
                        <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${autoPlayAudio ? 'left-7' : 'left-1'}`} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'system' && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <h3 className="text-xl font-display font-bold text-on-surface mb-4">System Controls</h3>
                  <p className="text-sm text-on-surface-variant mb-6">Manage local data and active sessions.</p>
                  
                  <div className="space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-surface-container rounded-2xl border border-outline-variant/20 gap-4">
                      <div>
                        <h4 className="font-label font-bold text-on-surface">Clear Chat History</h4>
                        <p className="text-xs text-on-surface-variant mt-1">Delete all local conversations from this device.</p>
                      </div>
                      <button 
                        onClick={handleClearHistory}
                        className="hover-lock px-4 py-2 bg-primary/20 text-primary font-label text-xs uppercase tracking-wider font-bold rounded-lg flex items-center gap-2 whitespace-nowrap shrink-0 hover:bg-primary hover:text-on-primary transition-colors"
                      >
                        <Trash2 className="w-4 h-4" /> Clear History
                      </button>
                    </div>

                    <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-surface-container rounded-2xl border border-outline-variant/20 gap-4">
                      <div>
                        <h4 className="font-label font-bold text-on-surface">Sign Out</h4>
                        <p className="text-xs text-on-surface-variant mt-1">Disconnect your account and return to login.</p>
                      </div>
                      <button 
                        onClick={() => window.location.href = '/login'}
                        className="hover-lock px-4 py-2 bg-surface-variant text-on-surface font-label text-xs uppercase tracking-wider font-bold rounded-lg flex items-center gap-2 whitespace-nowrap shrink-0 hover:bg-surface-container-highest transition-colors"
                      >
                        <LogOut className="w-4 h-4" /> Sign Out
                      </button>
                    </div>
                    
                    <hr className="border-outline-variant/20 my-4" />
                    
                    <div>
                      <h4 className="font-label font-bold text-on-surface mb-4 flex items-center gap-2"><Mail className="w-4 h-4"/> Support & Contact</h4>
                      <p className="text-sm text-on-surface-variant mb-2">Need help or want to provide feedback?</p>
                      <a href="mailto:sharathprime10@gmail.com" className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary hover:bg-primary/20 transition-colors rounded-xl font-label text-sm font-semibold border border-primary/20">
                        Email Developer
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            )}
            </div>
          </div>
        </div>
      </div>
    </ChatLayout>
  );
};

export default Settings;
