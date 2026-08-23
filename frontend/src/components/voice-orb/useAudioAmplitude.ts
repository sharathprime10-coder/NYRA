import { useEffect, useRef, useState } from 'react';
import { useMotionValue, MotionValue } from 'framer-motion';

export interface AudioAmplitudeControls {
  amplitude: MotionValue<number>;
  frequencies: Uint8Array;
}

export function useAudioAmplitude(
  source: MediaStream | HTMLAudioElement | null,
  isActive: boolean
): AudioAmplitudeControls {
  const amplitude = useMotionValue(0);
  const [frequencies, setFrequencies] = useState<Uint8Array>(new Uint8Array(0));
  
  const contextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | MediaElementAudioSourceNode | null>(null);
  const requestRef = useRef<number>(0);
  
  // Throttle state updates for frequencies so we don't kill React
  const lastReactUpdate = useRef<number>(0);

  useEffect(() => {
    if (!isActive) {
      amplitude.set(0);
      setFrequencies(new Uint8Array(0));
      return;
    }

    // If active but no source (Native TTS is speaking), simulate a rhythmic pulse
    if (!source) {
      const updateLoop = () => {
        const time = performance.now() / 1000;
        // Create a bouncy, talking-like rhythmic wave using sines
        const simulatedAmp = 0.3 + (Math.sin(time * 12) * 0.1) + (Math.sin(time * 4) * 0.2);
        const normalized = Math.max(0, Math.min(1, simulatedAmp));
        amplitude.set(normalized);
        requestRef.current = requestAnimationFrame(updateLoop);
      };
      updateLoop();
      
      return () => {
        cancelAnimationFrame(requestRef.current);
        amplitude.set(0);
      };
    }

    const initAudio = () => {
      // Create context if it doesn't exist
      if (!contextRef.current) {
        contextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }
      
      const ctx = contextRef.current;
      
      // Resume if suspended (browser policy)
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      if (!analyserRef.current) {
        analyserRef.current = ctx.createAnalyser();
        analyserRef.current.fftSize = 256;
        analyserRef.current.smoothingTimeConstant = 0.7;
      }
      
      const analyser = analyserRef.current;

      try {
        if (source instanceof MediaStream) {
          sourceNodeRef.current = ctx.createMediaStreamSource(source);
          sourceNodeRef.current.connect(analyser);
        } else if (source instanceof HTMLAudioElement) {
          // Reusing media element sources can throw if already created
          // To be safe, we wrap in try-catch or ensure we only create it once per element
          if (!(source as any)._hasSourceNode) {
            sourceNodeRef.current = ctx.createMediaElementSource(source);
            (source as any)._hasSourceNode = true;
          }
          if (sourceNodeRef.current) {
             sourceNodeRef.current.connect(analyser);
             analyser.connect(ctx.destination); // Must route back to destination to hear it
          }
        }
      } catch (e) {
        console.warn('Audio routing error:', e);
      }

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      setFrequencies(new Uint8Array(analyser.frequencyBinCount));

      const updateLoop = () => {
        analyser.getByteFrequencyData(dataArray);
        
        // Calculate average amplitude
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        
        // Normalize 0-1
        const normalized = Math.min(avg / 128, 1);
        amplitude.set(normalized);
        
        // Update frequencies state occasionally for the ticks (every ~50ms)
        const now = performance.now();
        if (now - lastReactUpdate.current > 50) {
          setFrequencies(new Uint8Array(dataArray));
          lastReactUpdate.current = now;
        }

        requestRef.current = requestAnimationFrame(updateLoop);
      };

      updateLoop();
    };

    initAudio();

    return () => {
      cancelAnimationFrame(requestRef.current);
      if (sourceNodeRef.current) {
        sourceNodeRef.current.disconnect();
        sourceNodeRef.current = null;
      }
      // If we connected to destination (TTS), we should disconnect analyser from destination too
      if (analyserRef.current && source instanceof HTMLAudioElement) {
        analyserRef.current.disconnect();
      }
    };
  }, [source, isActive, amplitude]);

  return { amplitude, frequencies };
}
