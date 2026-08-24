import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import api from '../api/client';

interface CinematicVoiceOrbProps {
  onClose: () => void;
  onMessageTranscribed: (msg: string, response: string, newSessionId?: string) => void;
  sessionId?: string;
}

type OrbState = 'init' | 'greeting' | 'listening' | 'processing' | 'speaking';

class ErrorBoundary extends React.Component<{ onClose: () => void, children: React.ReactNode }, { hasError: boolean, error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error("VoiceOrb Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 z-[300] bg-red-900 text-white p-10 flex flex-col items-center justify-center font-body">
          <h1 className="text-2xl font-bold mb-4 text-center">Voice Assistant Crashed</h1>
          <p className="mb-4 text-center">Please take a screenshot of this error for the developer:</p>
          <pre className="text-sm bg-black/50 p-4 rounded overflow-auto max-w-2xl text-left whitespace-pre-wrap">
            {this.state.error?.toString()}
            {'\n'}
            {this.state.error?.stack}
          </pre>
          <button onClick={this.props.onClose} className="mt-8 px-6 py-2 bg-white text-red-900 rounded-full font-bold hover:bg-gray-200">
            Close and Return to Chat
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const CinematicVoiceOrbInner: React.FC<CinematicVoiceOrbProps> = ({ onClose, onMessageTranscribed, sessionId }) => {
  const [orbState, setOrbState] = useState<OrbState>('init');
  const [transcript, setTranscript] = useState('');
  
  const recognitionRef = useRef<any>(null);
  const orbStateRef = useRef<OrbState>('init');
  const sessionIdRef = useRef<string | undefined>(sessionId);
  const silenceTimerRef = useRef<any>(null);
  const accumulatedTranscriptRef = useRef<string>('');

  useEffect(() => {
    orbStateRef.current = orbState;
  }, [orbState]);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);
  
  // Safe access to speechSynthesis
  const synth = typeof window !== 'undefined' ? window.speechSynthesis : null;

  useEffect(() => {
    let timer: any;
    
    try {
      // Setup Speech Recognition
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        
        // Match recognition language to the selected TTS voice
        const savedVoiceName = localStorage.getItem('nyra_voice');
        let targetLang = 'en-US';
        if (synth && savedVoiceName) {
            const voices = synth.getVoices();
            const foundVoice = voices.find((v: any) => v.name === savedVoiceName);
            if (foundVoice) {
                targetLang = foundVoice.lang;
            }
        }
        recognitionRef.current.lang = targetLang;

        recognitionRef.current.onresult = (event: any) => {
          if (orbStateRef.current !== 'listening') return;
          
          let finalTranscript = '';
          let interimTranscript = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }
          
          if (interimTranscript) {
             setTranscript((accumulatedTranscriptRef.current + " " + interimTranscript).trim());
             if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
          }
          
          if (finalTranscript) {
            accumulatedTranscriptRef.current = (accumulatedTranscriptRef.current + " " + finalTranscript).trim();
            setTranscript(accumulatedTranscriptRef.current);
            
            if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
            
            silenceTimerRef.current = setTimeout(() => {
                const finalQuery = accumulatedTranscriptRef.current.trim();
                if (finalQuery) {
                    accumulatedTranscriptRef.current = "";
                    handleProcessQuery(finalQuery);
                }
            }, 3000);
          }
        };
        
        recognitionRef.current.onerror = (event: any) => {
           console.error('Speech recognition error', event.error);
           if (event.error === 'no-speech' && orbStateRef.current === 'listening') {
               try { recognitionRef.current?.start(); } catch(e) {}
           } else {
               setOrbState('listening');
           }
        };
        
        recognitionRef.current.onend = () => {
           // Auto-restart if we are supposed to be listening but it ended
           if (orbStateRef.current === 'listening') {
               try { recognitionRef.current?.start(); } catch(e) {}
           }
        };
      }

      // Force load voices
      if (synth) synth.getVoices();

      // Initial greeting sequence
      timer = setTimeout(() => {
        setOrbState('greeting');
        speak("Hello. How can I help you?", () => {
          setOrbState('listening');
        });
      }, 300);

    } catch (e) {
      console.error("Initialization error in VoiceOrb:", e);
      throw e; // Let ErrorBoundary catch it
    }

    return () => {
      if (timer) clearTimeout(timer);
      try {
        if (recognitionRef.current) {
            recognitionRef.current.onend = null;
            recognitionRef.current.abort();
        }
        if (synth) synth.cancel();
      } catch (e) {
        console.error("Cleanup error in VoiceOrb:", e);
      }
    };
  }, []);

  useEffect(() => {
    if (orbState === 'listening' && recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch(e) {
        console.log("Recognition already started or failed to start", e);
      }
    } else if (orbState !== 'listening' && recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch(e) {}
    }
  }, [orbState]);

  const speak = (text: string, onEnd?: () => void) => {
    if (!synth) {
       if(onEnd) onEnd();
       return;
    }

    try {
      synth.cancel(); // clear queue
      const utterThis = new SpeechSynthesisUtterance(text);
      const savedVoiceName = localStorage.getItem('nyra_voice');
      const savedSpeed = parseFloat(localStorage.getItem('nyra_speed') || '1.0');
      const voices = synth.getVoices();

      let preferredVoice = voices[0];
      if (savedVoiceName) {
        const found = voices.find((v: any) => v.name === savedVoiceName);
        if (found) preferredVoice = found;
      } else {
        preferredVoice = voices.find((v: any) => v.name.includes('Google US English')) || voices.find((v: any) => v.lang === 'en-US') || voices[0];
      }
      
      if (preferredVoice) {
          utterThis.voice = preferredVoice;
      }
      
      utterThis.pitch = 1.1; 
      utterThis.rate = savedSpeed;
      
      utterThis.onend = () => {
         if(onEnd) onEnd();
      };
      
      utterThis.onerror = () => {
         if(onEnd) onEnd();
      };
      
      synth.speak(utterThis);
    } catch(e) {
      console.error("Speech synthesis error", e);
      if(onEnd) onEnd();
    }
  };

  const handleProcessQuery = async (text: string) => {
    setOrbState('processing');
    
    try {
      const savedVoiceName = localStorage.getItem('nyra_voice') || 'Default';
      const languageHint = `\n\n[System Instruction: You are responding via Text-to-Speech. The user's voice setting is '${savedVoiceName}'. You MUST respond in the appropriate language for this voice. Keep your answer concise and conversational.]`;

      const token = localStorage.getItem('token');
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          message: text + languageHint,
          session_id: sessionIdRef.current,
          stream: true
        })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No reader");

      // Sentence-by-sentence TTS: buffer tokens, speak complete sentences
      let fullAnswer = '';
      let sentenceBuffer = '';
      let newSessionId: string | undefined;
      const sentenceQueue: string[] = [];
      let isSpeakingQueue = false;

      const speakNextInQueue = () => {
        if (sentenceQueue.length === 0) {
          isSpeakingQueue = false;
          return;
        }
        isSpeakingQueue = true;
        const sentence = sentenceQueue.shift()!;
        speak(sentence, speakNextInQueue);
      };

      const enqueueSentence = (sentence: string) => {
        const trimmed = sentence.trim();
        if (!trimmed) return;
        sentenceQueue.push(trimmed);
        if (!isSpeakingQueue) {
          setOrbState('speaking');
          speakNextInQueue();
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.event === 'token') {
                fullAnswer += data.content;
                sentenceBuffer += data.content;

                // Check if buffer contains a complete sentence
                const sentenceEnd = sentenceBuffer.search(/[.!?]\s|[.!?]$/);
                if (sentenceEnd !== -1) {
                  const endIdx = sentenceEnd + 1;
                  const completeSentence = sentenceBuffer.slice(0, endIdx);
                  sentenceBuffer = sentenceBuffer.slice(endIdx);
                  enqueueSentence(completeSentence);
                }
              } else if (data.event === 'end') {
                if (data.session_id) newSessionId = data.session_id;
              }
            } catch (e) {
              // skip malformed SSE lines
            }
          }
        }
      }

      // Flush remaining buffer
      if (sentenceBuffer.trim()) {
        enqueueSentence(sentenceBuffer);
        sentenceBuffer = '';
      }

      // Wait for all speech to finish, then report back
      const waitForSpeechDone = () => {
        return new Promise<void>((resolve) => {
          const check = () => {
            if (!isSpeakingQueue && sentenceQueue.length === 0) {
              resolve();
            } else {
              setTimeout(check, 200);
            }
          };
          check();
        });
      };

      await waitForSpeechDone();

      onMessageTranscribed(text, fullAnswer, newSessionId);
      setTranscript('');
      setOrbState('listening');

    } catch (err) {
      console.error(err);
      speak("I'm sorry, I encountered an error.", () => {
        setTranscript('');
        setOrbState('listening');
      });
    }
  };

  const handleClose = () => {
      try {
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        if (recognitionRef.current) {
            recognitionRef.current.onend = null;
            recognitionRef.current.abort();
        }
        if (synth) synth.cancel();
      } catch (e) {}
      onClose();
  };

  const getOrbClasses = () => {
    switch (orbState) {
      case 'init': return 'scale-90 opacity-70 animate-pulse';
      case 'greeting': return 'scale-110 opacity-100 orb-speaking';
      case 'listening': return 'scale-100 opacity-90 orb-listening';
      case 'processing': return 'scale-105 opacity-100 orb-processing';
      case 'speaking': return 'scale-110 opacity-100 orb-speaking';
      default: return 'scale-100 opacity-80';
    }
  };

  const getRingClasses = () => {
    switch (orbState) {
      case 'init': return 'scale-90 opacity-50 animate-spin-slow';
      case 'greeting': return 'scale-125 opacity-100 animate-spin-fast ring-speaking';
      case 'listening': return 'scale-110 opacity-80 animate-spin-slow ring-listening';
      case 'processing': return 'scale-90 opacity-100 animate-spin-fast ring-processing';
      case 'speaking': return 'scale-125 opacity-100 animate-spin-fast ring-speaking';
      default: return 'scale-100 opacity-50 animate-spin-slow';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 1 }}
      className="fixed inset-0 z-[200] bg-black overflow-hidden flex flex-col items-center justify-center font-body"
    >
      <div className="absolute top-0 left-0 w-full p-6 flex justify-between items-center z-50">
        <button 
          onClick={handleClose}
          className="w-12 h-12 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-white/70 hover:text-white transition-all backdrop-blur-md"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
      </div>

      <div className="relative flex items-center justify-center w-full max-w-2xl aspect-square pointer-events-none perspective-1000">
        {/* Vibrating Outer Waves */}
        <div className={`absolute w-[120%] h-[120%] rounded-full bg-gradient-to-tr from-blue-900/30 via-transparent to-cyan-900/30 blur-[60px] transition-all duration-1000 ${orbState === 'processing' ? 'opacity-100 scale-125 animate-pulse' : 'opacity-60 scale-100 animate-pulse-glow'}`}></div>

        {/* Wireframe Neon Orb */}
        <div className={`absolute w-[45%] h-[45%] border-[1px] border-cyan-400/80 shadow-[0_0_20px_rgba(34,211,238,0.6),inset_0_0_20px_rgba(34,211,238,0.4)] transition-all duration-[1500ms] ${getRingClasses()}`} style={{ animationDirection: 'normal', borderRadius: '40% 60% 70% 30% / 40% 50% 60% 50%' }}></div>
        <div className={`absolute w-[47%] h-[47%] border-[1px] border-blue-500/70 shadow-[0_0_15px_rgba(59,130,246,0.5),inset_0_0_15px_rgba(59,130,246,0.3)] transition-all duration-[1200ms] ${getRingClasses()}`} style={{ animationDirection: 'reverse', borderRadius: '60% 40% 30% 70% / 50% 40% 50% 60%' }}></div>
        <div className={`absolute w-[43%] h-[43%] border-[2px] border-blue-400/90 shadow-[0_0_25px_rgba(96,165,250,0.7),inset_0_0_25px_rgba(96,165,250,0.5)] transition-all duration-[1000ms] ${getRingClasses()}`} style={{ animationDirection: 'normal', borderRadius: '50% 50% 60% 40% / 60% 30% 70% 40%' }}></div>
        <div className={`absolute w-[48%] h-[48%] border-[1px] border-cyan-300/60 shadow-[0_0_10px_rgba(103,232,249,0.4)] transition-all duration-[2000ms] ${getRingClasses()}`} style={{ animationDirection: 'reverse', borderRadius: '30% 70% 50% 50% / 50% 60% 40% 50%' }}></div>
        
        {/* Core Glow */}
        <div className={`relative w-[30%] h-[30%] rounded-full transition-all duration-[800ms] ease-out ${getOrbClasses()}`}>
            <div className="absolute inset-0 rounded-full bg-blue-900/10 blur-[20px] mix-blend-screen"></div>
        </div>

        <div className="absolute bottom-10 text-center w-full">
           <AnimatePresence mode="wait">
             <motion.p
               key={orbState}
               initial={{ opacity: 0, y: 10 }}
               animate={{ opacity: 1, y: 0 }}
               exit={{ opacity: 0, y: -10 }}
               className="font-label text-xs tracking-[0.3em] uppercase text-white/50"
             >
               {orbState}
             </motion.p>
           </AnimatePresence>
           
           <AnimatePresence>
               {transcript ? (
                   <motion.p
                     key="transcript-text"
                     initial={{ opacity: 0 }}
                     animate={{ opacity: 1 }}
                     exit={{ opacity: 0 }}
                     className="mt-4 text-white/80 font-body text-sm max-w-md mx-auto text-center"
                   >
                       "{transcript}"
                   </motion.p>
               ) : null}
           </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
};

const CinematicVoiceOrb: React.FC<CinematicVoiceOrbProps> = (props) => {
  return createPortal(
    <ErrorBoundary onClose={props.onClose}>
      <CinematicVoiceOrbInner {...props} />
    </ErrorBoundary>,
    document.body
  );
};

export default CinematicVoiceOrb;
