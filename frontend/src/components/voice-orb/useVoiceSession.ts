import { useState, useEffect, useRef, useCallback } from 'react';
import { useSpeechToText } from '../../hooks/useSpeechToText';

export type VoiceState = 'entering' | 'idle' | 'listening' | 'thinking' | 'speaking';

export function useVoiceSession(onClose: () => void) {
  const [state, setState] = useState<VoiceState>('entering');
  const [transcript, setTranscript] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  
  const [micStream, setMicStream] = useState<MediaStream | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const [ttsAudio, setTtsAudio] = useState<HTMLAudioElement | null>(null);

  // Auto-transition from entering -> idle
  useEffect(() => {
    if (state === 'entering') {
      const t = setTimeout(() => {
        setState('idle');
      }, 800); // Wait for enter animation
      return () => clearTimeout(t);
    }
  }, [state]);

  const { isListening, toggleListening, supported } = useSpeechToText({
    onResult: (text, isFinal) => {
      setTranscript(prev => {
         // simple concat for demo, or replace
         return text; 
      });
      if (isFinal) {
        handleSilenceDetected(text);
      }
    }
  });

  // Handle acquiring mic for visuals
  useEffect(() => {
    if (state === 'listening' && !micStream) {
      navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        .then(stream => {
          setMicStream(stream);
        })
        .catch(err => console.error("Could not get mic for visualizer", err));
    }
    return () => {
      if (state !== 'listening' && micStream) {
        micStream.getTracks().forEach(t => t.stop());
        setMicStream(null);
      }
    };
  }, [state, micStream]);

  // Speech processing
  const handleSilenceDetected = useCallback(async (finalText: string) => {
    if (!finalText.trim()) {
      setState('idle');
      return;
    }
    
    setState('thinking');
    if (isListening) {
      toggleListening();
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          message: finalText,
          thinking_level: 'low',
          tone: 'default'
        })
      });

      if (!response.ok) throw new Error("API Error");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      if (reader) {
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
                  fullResponse += data.content;
                  setAiResponse(fullResponse);
                }
              } catch (e) {}
            }
          }
        }
      }

      // Start speaking
      playTTS(fullResponse);

    } catch (e) {
      console.error(e);
      setState('idle');
      setAiResponse("I'm sorry, I encountered an error.");
    }
  }, [isListening, toggleListening]);

  const playTTS = (text: string) => {
    setState('speaking');
    
    const synth = window.speechSynthesis;
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Load preferred voice and speed from settings
    const preferredVoiceName = localStorage.getItem('nyra_voice');
    if (preferredVoiceName) {
      const voices = synth.getVoices();
      const voice = voices.find(v => v.name === preferredVoiceName);
      if (voice) {
        utterance.voice = voice;
      }
    }
    
    const speed = parseFloat(localStorage.getItem('nyra_speed') || '1.0');
    utterance.rate = speed;
    
    utterance.onend = () => {
      setState('idle');
      setTranscript('');
      setAiResponse('');
    };
    
    utterance.onerror = () => {
      setState('idle');
      setTranscript('');
      setAiResponse('');
    };

    synth.speak(utterance);
  };

  const toggleMic = () => {
    if (state === 'listening') {
      toggleListening();
      setState('thinking');
    } else if (state === 'idle') {
      setTranscript('');
      setAiResponse('');
      toggleListening();
      setState('listening');
    } else if (state === 'speaking') {
      // interrupt
      if (audioElRef.current) audioElRef.current.pause();
      window.speechSynthesis.cancel();
      setState('idle');
    }
  };

  const cancelAndClose = () => {
    if (isListening) toggleListening();
    if (audioElRef.current) {
      audioElRef.current.pause();
      audioElRef.current.src = "";
    }
    window.speechSynthesis.cancel();
    if (micStream) {
      micStream.getTracks().forEach(t => t.stop());
    }
    onClose();
  };

  return {
    state,
    transcript,
    aiResponse,
    micStream,
    ttsAudio,
    toggleMic,
    cancelAndClose
  };
}
