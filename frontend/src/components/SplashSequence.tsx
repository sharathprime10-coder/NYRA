import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface SplashSequenceProps {
  onComplete: () => void;
}

const SplashSequence: React.FC<SplashSequenceProps> = ({ onComplete }) => {
  const [phase, setPhase] = useState<'logo' | 'complete'>('logo');

  useEffect(() => {
    // Phase 1: Logo display
    const timer1 = setTimeout(() => {
      setPhase('complete');
      setTimeout(onComplete, 1000); // Wait for fade out
    }, 2500);

    return () => {
      clearTimeout(timer1);
    };
  }, [onComplete]);

  return (
    <AnimatePresence>
      {phase !== 'complete' && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1, ease: "easeInOut" }}
          className="fixed inset-0 z-[100] bg-black overflow-hidden flex items-center justify-center"
        >
          {/* Phase 1: NYRA Logo Sequence */}
          <AnimatePresence>
            {phase === 'logo' && (
              <motion.div
                key="logo-phase"
                initial={{ scale: 0.8, opacity: 0, filter: 'blur(10px)' }}
                animate={{ scale: 1, opacity: 1, filter: 'blur(0px)' }}
                exit={{ scale: 1.5, opacity: 0, filter: 'blur(20px)' }}
                transition={{ duration: 1.5, ease: "easeInOut" }}
                className="flex flex-col items-center justify-center gap-6"
              >
                {/* Custom slick animated logo */}
                <div className="relative w-40 h-40">
                  <div className="absolute inset-0 rounded-full bg-primary/20 blur-xl animate-pulse"></div>
                  <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuB1owtDrGiK0eLLr0TiFNNHaZuvX2WhyFxW8q0XM6csuaJeTvZUOHW-0sv9XITQuO8qC31-UYdvXXHJ7gaCZEpZjyR-U0sH8d4pym7yY3-wHcl2eTjwtjBz1x5MFjsJFCFWK4A3-Ld9s9NLGxYvyrRzudMezd2ptn2NMrhuOrKh-5D_QVEa1bZahSL5bXJ5rAROMZ_3-PFnuR7qt1Lwhm6IkpFVT-AY0--f1jDzEQtr361yI64qWV1DUvOjviMQAKyEkag" alt="NYRA" className="w-full h-full object-contain drop-shadow-[0_0_30px_rgba(47,217,244,0.6)] relative z-10 rounded-2xl" />
                </div>
                <h1 className="font-display text-6xl font-extrabold tracking-[0.3em] text-transparent bg-clip-text bg-gradient-to-r from-white via-primary-container to-white">NYRA</h1>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default SplashSequence;
