import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Home, MessageSquare, LayoutDashboard } from 'lucide-react';

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden p-6">
      <div className="absolute inset-0 bg-background/80 backdrop-blur-3xl"></div>
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-10 rounded-2xl max-w-lg w-full text-center relative z-10"
      >
        <h1 className="text-8xl font-display font-bold gradient-text mb-4">404</h1>
        <h2 className="text-2xl font-body font-semibold text-on-surface mb-4">Wandered off the map?</h2>
        <p className="text-on-surface-variant font-body mb-10 text-lg">
          The page you're looking for doesn't exist or has been moved to another dimension.
        </p>

        <div className="flex flex-col gap-4">
          <button 
            onClick={() => navigate('/')}
            className="w-full flex items-center justify-center gap-2 p-4 rounded-xl bg-gradient-to-r from-primary to-inverse-primary text-on-primary font-label font-bold uppercase tracking-wider hover:opacity-90 transition-opacity"
          >
            <Home className="w-5 h-5" /> Back to Home
          </button>
          
          <div className="flex gap-4">
            <button 
              onClick={() => navigate('/dashboard')}
              className="flex-1 flex items-center justify-center gap-2 p-4 rounded-xl bg-surface/50 border border-outline-variant/30 text-on-surface hover:bg-surface transition-colors font-label uppercase tracking-wider text-sm font-semibold"
            >
              <LayoutDashboard className="w-4 h-4" /> Dashboard
            </button>
            <button 
              onClick={() => navigate('/chat')}
              className="flex-1 flex items-center justify-center gap-2 p-4 rounded-xl bg-surface/50 border border-outline-variant/30 text-on-surface hover:bg-surface transition-colors font-label uppercase tracking-wider text-sm font-semibold"
            >
              <MessageSquare className="w-4 h-4" /> Chat
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default NotFound;
