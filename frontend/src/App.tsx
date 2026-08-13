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
    <>
      {showSplash && <SplashSequence onComplete={() => setShowSplash(false)} />}
      <Router>
        <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Welcome />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/chat/:sessionId" element={<Chat />} />
        <Route path="/knowledge" element={<KnowledgeBase />} />
        <Route path="/voice" element={<Voice />} />
        <Route path="/history" element={<History />} />
        <Route path="/search" element={<Search />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
    </>
  );
};

export default App;
