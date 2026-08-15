import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import SplashSequence from './components/SplashSequence';
import Login from './components/Login';
import Welcome from './components/Welcome';
import Chat from './components/Chat';
import KnowledgeBase from './components/KnowledgeBase';
import Voice from './components/Voice';

import History from './components/History';
import Search from './components/Search';
import Settings from './components/Settings';
import Onboarding from './components/Onboarding';
import AdminCuration from './components/AdminCuration';
import NotFound from './components/NotFound';
import ThankYou from './components/ThankYou';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { MessageSquare } from 'lucide-react';

const App: React.FC = () => {
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    const theme = localStorage.getItem('nyra_theme') || 'dark';
    if (theme === 'light') {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
      document.documentElement.classList.add('dark');
    }
  }, []);

  return (
    <div className="bg-[#0b0c10] min-h-screen text-white font-sans selection:bg-indigo-500/30 pb-20 md:pb-0">
      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-20 pointer-events-none mix-blend-screen"></div>
      <div className="relative z-10 flex flex-col min-h-screen">
        {showSplash && <SplashSequence onComplete={() => setShowSplash(false)} />}
        <Router>
          <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/dashboard" element={<Welcome />} />
          <Route path="/chat" element={<ErrorBoundary name="Chat"><Chat /></ErrorBoundary>} />
          <Route path="/chat/:sessionId" element={<ErrorBoundary name="Chat"><Chat /></ErrorBoundary>} />
          <Route path="/knowledge" element={<ErrorBoundary name="Knowledge Base"><KnowledgeBase /></ErrorBoundary>} />
          <Route path="/voice" element={<ErrorBoundary name="Voice Mode"><Voice /></ErrorBoundary>} />
          <Route path="/history" element={<ErrorBoundary name="History"><History /></ErrorBoundary>} />
          <Route path="/search" element={<Search />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/admin/curation" element={<AdminCuration />} />
          <Route path="/thank-you" element={<ThankYou />} />
          <Route path="*" element={<NotFound />} />
          </Routes>
          
          {/* Sticky Mobile CTA */}
          <div className="md:hidden fixed bottom-0 left-0 right-0 p-4 bg-background/80 backdrop-blur-xl border-t border-white/10 z-[100]">
            <a href="/chat" className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-primary to-inverse-primary text-on-primary font-label font-bold py-3 px-4 rounded-xl shadow-lg shadow-primary/20">
              <MessageSquare className="w-5 h-5" /> Start Chatting
            </a>
          </div>
        </Router>
      </div>
    </div>
  );
};

export default App;
