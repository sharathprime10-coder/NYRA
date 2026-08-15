import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, ArrowRight } from 'lucide-react';
import confetti from 'canvas-confetti';

const ThankYou: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#8083FF', '#C0C1FF', '#2FD9F4']
    });
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden p-6">
      <div className="absolute inset-0 bg-background/80 backdrop-blur-3xl"></div>
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-panel p-10 rounded-2xl max-w-md w-full text-center relative z-10"
      >
        <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="w-10 h-10 text-emerald-400" />
        </div>
        
        <h1 className="text-3xl font-display font-bold text-on-surface mb-2">Thank You!</h1>
        <p className="text-on-surface-variant font-body mb-10">
          Your details have been successfully saved. Welcome aboard.
        </p>

        <button 
          onClick={() => navigate('/dashboard')}
          className="w-full flex items-center justify-center gap-2 p-4 rounded-xl bg-gradient-to-r from-primary to-inverse-primary text-on-primary font-label font-bold uppercase tracking-wider hover:opacity-90 transition-opacity"
        >
          Continue to Dashboard <ArrowRight className="w-5 h-5" />
        </button>
      </motion.div>
    </div>
  );
};

export default ThankYou;
