import { useState, useEffect, useRef, useCallback } from 'react';

interface UseSpeechToTextProps {
  onResult: (text: string, isFinal: boolean) => void;
}

export const useSpeechToText = ({ onResult }: UseSpeechToTextProps) => {
  const [isListening, setIsListening] = useState(false);
  const [supported, setSupported] = useState(true);
  
  // Need to handle vendor prefixes for SpeechRecognition
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!SpeechRecognition) {
      setSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      // Reset silence timer whenever we get a result
      resetSilenceTimer();

      if (finalTranscript || interimTranscript) {
        onResult(finalTranscript || interimTranscript, !!finalTranscript);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error', event.error);
      stopListening();
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }
    };
  }, [onResult]);

  const resetSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
    }
    // Auto-stop after 2 seconds of silence
    silenceTimerRef.current = setTimeout(() => {
      stopListening();
    }, 2000);
  }, []);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.start();
      setIsListening(true);
      resetSilenceTimer();
    } catch (e) {
      console.error(e);
    }
  }, [resetSilenceTimer]);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
      setIsListening(false);
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  return {
    isListening,
    supported,
    startListening,
    stopListening,
    toggleListening
  };
};
