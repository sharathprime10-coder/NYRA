import React from 'react';
import { Menu, Bell, User } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const Header: React.FC = () => {
  const { user } = useAuth();
  return (
    <header className="bg-transparent fixed top-0 right-0 w-full md:w-[calc(100%-280px)] z-40 flex justify-between items-center h-16 px-4 md:px-8">
      {/* Mobile Menu Trigger & Logo */}
      <div className="flex items-center gap-4 md:hidden">
        <button className="text-on-surface-variant hover:text-primary transition-all hover-lock rounded-lg p-1">
          <Menu className="w-6 h-6" />
        </button>
        <div className="flex items-center gap-2">
          <img alt="NYRA Logo" className="w-8 h-8 object-contain drop-shadow-lg rounded-lg" src="/nyra_logo.jpg" />
          <span className="font-display text-2xl font-extrabold text-on-surface">NYRA</span>
        </div>
      </div>
      
      {/* Desktop Logo Spacer */}
      <div className="hidden md:block font-display text-2xl font-extrabold text-on-surface"></div>
      
      {/* Navigation Links */}
      <nav className="hidden md:flex items-center gap-6">
        <Link to="/chat" className="text-primary border-b-2 border-primary pb-2 font-medium">Chat</Link>
        <Link to="/knowledge" className="text-on-surface-variant hover:text-primary transition-all font-medium">Sources</Link>
      </nav>
      
      {/* Trailing Actions */}
      <div className="flex items-center gap-4">
        <button className="text-on-surface-variant hover:text-primary transition-all hover-lock rounded-full overflow-hidden w-8 h-8 flex items-center justify-center border border-on-surface-variant/20 p-0" title={user?.display_name || 'Profile'}>
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt={user.display_name || 'Profile'} className="w-full h-full object-cover" />
          ) : (
            <User className="w-5 h-5" />
          )}
        </button>
      </div>
    </header>
  );
};

export default Header;
