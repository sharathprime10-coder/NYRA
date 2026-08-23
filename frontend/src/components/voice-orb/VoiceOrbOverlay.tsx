import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useVoiceSession } from './useVoiceSession';
import { useAudioAmplitude } from './useAudioAmplitude';
import { Orb } from './Orb';

interface VoiceOrbOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export function VoiceOrbOverlay({ isOpen, onClose }: VoiceOrbOverlayProps) {
  return createPortal(
    <AnimatePresence>
      {isOpen && <VoiceOrbOverlayContent onClose={onClose} />}
    </AnimatePresence>,
    document.body
  );
}

function VoiceOrbOverlayContent({ onClose }: { onClose: () => void }) {
  const {
    state,
    transcript,
    aiResponse,
    micStream,
    ttsAudio,
    toggleMic,
    cancelAndClose
  } = useVoiceSession(onClose);

  // We only track mic amplitude during listening, and tts amplitude during speaking
  const source = state === 'listening' ? micStream : (state === 'speaking' ? ttsAudio : null);
  const isActive = state === 'listening' || state === 'speaking';
  
  const { amplitude, frequencies } = useAudioAmplitude(source, isActive);

  // Listen for Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') cancelAndClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [cancelAndClose]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(24px)' }}
      onClick={(e) => {
        // Close if clicking the backdrop directly
        if (e.target === e.currentTarget) cancelAndClose();
      }}
    >
      <button 
        onClick={cancelAndClose}
        className="absolute top-6 right-6 p-3 rounded-full bg-white/5 hover:bg-white/10 text-white transition-colors"
      >
        <X className="w-6 h-6" />
      </button>

      <div className="relative flex flex-col items-center justify-center w-full max-w-2xl px-6">
        
        {/* Orb Container (clickable to toggle listening) */}
        <div 
          className="relative cursor-pointer group" 
          onClick={toggleMic}
          title={state === 'idle' ? "Tap to speak" : "Tap to stop"}
        >
          <Orb state={state} amplitude={amplitude} size={300} />
        </div>

        {/* Caption Area */}
        <div className="mt-20 h-24 flex items-center justify-center text-center">
          <AnimatePresence mode="wait">
            {state === 'listening' && (
              <motion.p
                key="listening-text"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-white/80 text-lg sm:text-xl font-medium tracking-wide max-w-lg"
              >
                {transcript || "I'm listening..."}
              </motion.p>
            )}

            {state === 'thinking' && (
              <motion.p
                key="thinking-text"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-indigo-300 text-lg font-medium tracking-wide"
              >
                Thinking...
              </motion.p>
            )}

            {state === 'speaking' && (
              <motion.p
                key="speaking-text"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-white text-xl sm:text-2xl font-semibold tracking-wide max-w-xl leading-relaxed"
              >
                {aiResponse}
              </motion.p>
            )}
            
            {state === 'idle' && (
              <motion.p
                key="idle-text"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-white/40 text-sm font-medium tracking-wide"
              >
                Tap the orb to speak
              </motion.p>
            )}
          </AnimatePresence>
        </div>

      </div>
    </motion.div>
  );
}
