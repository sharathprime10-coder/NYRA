import React from 'react';
import { Plus, History, Database, Search, Settings } from 'lucide-react';
import { Link } from 'react-router-dom';

const Sidebar: React.FC = () => {
  return (
    <aside className="hidden md:flex w-[280px] h-screen fixed left-0 top-0 border-r border-outline-variant/10 shadow-2xl shadow-primary/5 bg-surface/40 backdrop-blur-xl flex-col p-6 gap-4 z-50">
      {/* Header */}
      <div className="mb-8 flex items-center gap-4 hover-lock p-2 rounded-xl cursor-pointer">
        <div className="w-10 h-10 rounded-xl overflow-hidden flex items-center justify-center flex-shrink-0 bg-surface-container">
          <img alt="NYRA Logo" className="w-8 h-8 object-contain drop-shadow-lg rounded-lg" src="/nyra_logo.jpg" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tighter text-on-surface">NYRA</h1>
          <p className="font-label text-xs text-on-surface-variant font-medium">Premium Knowledge Assistant</p>
        </div>
      </div>
      
      {/* Navigation Tabs */}
      <nav className="flex-1 flex flex-col gap-2">
        <Link to="/chat" className="flex items-center gap-3 p-3 bg-primary-container/30 text-primary font-semibold rounded-xl hover-lock">
          <Plus className="w-5 h-5" />
          <span className="font-label text-xs">New Chat</span>
        </Link>
        <Link to="/history" className="flex items-center gap-3 p-3 text-on-surface-variant hover:text-on-surface hover:bg-white/5 rounded-xl hover-lock font-medium">
          <History className="w-5 h-5" />
          <span className="font-label text-xs">History</span>
        </Link>
        <Link to="/knowledge" className="flex items-center gap-3 p-3 text-on-surface-variant hover:text-on-surface hover:bg-white/5 rounded-xl hover-lock font-medium">
          <Database className="w-5 h-5" />
          <span className="font-label text-xs">Knowledge Base</span>
        </Link>
        <Link to="/settings" className="flex items-center gap-3 p-3 text-on-surface-variant hover:text-on-surface hover:bg-white/5 rounded-xl hover-lock mt-auto font-medium">
          <Settings className="w-5 h-5" />
          <span className="font-label text-xs">Settings</span>
        </Link>
      </nav>
    </aside>
  );
};

export default Sidebar;
