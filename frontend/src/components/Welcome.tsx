import React, { useEffect, useRef, useState } from 'react';
import { ArrowRight, Compass, Settings, Database, PlusCircle, Mic } from 'lucide-react';
import { Link } from 'react-router-dom';
import TiltCard from './common/TiltCard';
import FluidBackground from './common/FluidBackground';
import { useAuth } from '../context/AuthContext';
const Welcome: React.FC = () => {
  const bg1Ref = useRef<HTMLImageElement>(null);
  const bg2Ref = useRef<HTMLImageElement>(null);
  const particlesRef = useRef<HTMLDivElement>(null);
  const [scrolled, setScrolled] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    // Parallax logic
    const handleMouseMove = (e: MouseEvent) => {
      const mouseX = e.clientX / window.innerWidth - 0.5;
      const mouseY = e.clientY / window.innerHeight - 0.5;

      if (bg1Ref.current) {
        const bgMoveX = mouseX * -20;
        const bgMoveY = mouseY * -20;
        bg1Ref.current.style.transform = `scale(1.1) translate(${bgMoveX}px, ${bgMoveY}px)`;
      }
      if (bg2Ref.current) {
        const bgMoveX = mouseX * -40;
        const bgMoveY = mouseY * -40;
        bg2Ref.current.style.transform = `scale(1.1) translate(${bgMoveX}px, ${bgMoveY}px)`;
      }

      if (particlesRef.current) {
        const particles = Array.from(particlesRef.current.children) as HTMLElement[];
        particles.forEach((p, index) => {
          const depth = (index % 5) + 1;
          const moveX = mouseX * depth * 20;
          const moveY = mouseY * depth * 20;
          p.style.transform = `translate(${moveX}px, ${moveY}px)`;
        });
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    return () => document.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    // Particles creation
    if (!particlesRef.current) return;
    const container = particlesRef.current;
    container.innerHTML = ''; // clear if re-run

    for (let i = 0; i < 30; i++) {
      const p = document.createElement('div');
      p.className = 'particle';
      const size = Math.random() * 3 + 1;
      p.style.width = `${size}px`;
      p.style.height = `${size}px`;
      p.style.left = `${Math.random() * 100}vw`;
      p.style.top = `${Math.random() * 100}vh`;
      container.appendChild(p);
    }
  }, []);

  useEffect(() => {
    // Scroll listener for navbar
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="dark bg-background text-on-background overflow-x-hidden min-h-screen relative font-body text-base selection:bg-primary-container selection:text-on-primary-container">
      {/* Atmospheric Fluid Background */}
      <FluidBackground />
      
      {/* Particle Layer */}
      <div ref={particlesRef} className="fixed inset-0 z-[-1] overflow-hidden pointer-events-none"></div>
      
      {/* Top Navigation */}
      <nav className={`fixed top-0 left-0 w-full z-50 flex justify-between items-center h-20 px-[20px] md:px-[64px] transition-all duration-300 animate-glide-in ${scrolled ? 'glass-panel border-b border-outline-variant/10' : 'bg-transparent'}`}>
        <div className="flex items-center gap-2 lock-on-hover rounded-xl px-2 py-1 cursor-pointer">
          <div className="w-10 h-10 rounded-lg overflow-hidden flex items-center justify-center shadow-[0_0_20px_rgba(73,75,214,0.3)] bg-surface-container">
            <img alt="NYRA Logo" className="w-8 h-8 object-contain rounded-lg" src="/logo.webp" />
          </div>
          <span className="font-display text-2xl font-extrabold tracking-tight hidden md:block">NYRA</span>
        </div>
        <div className="flex items-center gap-6">
          {user ? (
            <Link to="/chat" className="text-xs font-label font-semibold px-6 py-2.5 rounded-full border border-outline-variant/30 bg-surface-variant/20 hover:bg-surface-variant/50 backdrop-blur-md lock-on-hover flex items-center gap-2">
              <div className="w-5 h-5 rounded-full overflow-hidden bg-primary/20">
                {user.avatar_url && <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />}
              </div>
              Go to Dashboard
            </Link>
          ) : (
            <Link to="/login" className="text-xs font-label font-semibold px-6 py-2.5 rounded-full border border-outline-variant/30 bg-surface-variant/20 hover:bg-surface-variant/50 backdrop-blur-md lock-on-hover">
              Sign In
            </Link>
          )}
        </div>
      </nav>

      {/* Main Content Canvas */}
      <main className="relative z-10 pt-32 pb-20 px-[20px] md:px-[64px] min-h-screen flex flex-col items-center justify-center animate-glide-in">
        <div className="max-w-4xl mx-auto w-full flex flex-col items-center justify-center gap-12 text-center">
          {/* Hero Copy */}
          <TiltCard className="flex flex-col items-center gap-8 z-20 glass-advanced holographic-border p-12 rounded-3xl">
            <div className="noise-overlay rounded-3xl"></div>
            <div style={{ transform: "translateZ(40px)" }} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass-panel border-primary/20 text-tertiary text-xs font-label uppercase tracking-widest mb-2 animate-pulse-glow lock-on-hover cursor-default font-semibold relative z-10">
              <Settings className="w-4 h-4" />
              <span>Intelligence Evolved</span>
            </div>
            <h1 style={{ transform: "translateZ(60px)" }} className="font-display text-[32px] md:text-[48px] text-on-surface leading-tight font-bold">
              Ask. Retrieve.<br/>
              <span className="text-gradient">Understand.</span>
            </h1>
            <p style={{ transform: "translateZ(30px)" }} className="font-body text-lg text-on-surface-variant max-w-2xl">
              A sentient lens into your data landscape. NYRA transforms scattered knowledge into actionable intelligence through cinematic retrieval and deep reasoning.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto mt-4 justify-center">
              <Link to="/chat" className="bg-gradient-primary text-white font-label text-xs uppercase tracking-wider font-semibold px-8 py-4 rounded-full flex items-center justify-center gap-2 group lock-on-hover">
                Start Chat
                <ArrowRight className="group-hover:translate-x-1 transition-transform w-5 h-5" />
              </Link>
              <Link to="/knowledge" className="glass-panel text-on-surface font-label text-xs uppercase tracking-wider font-semibold px-8 py-4 rounded-full flex items-center justify-center gap-2 border border-outline-variant/30 lock-on-hover">
                <Compass className="text-on-surface-variant group-hover:text-primary transition-colors w-5 h-5" />
                Explore Knowledge Base
              </Link>
            </div>
          </TiltCard>

          {/* Hero Visual / Chat Preview */}
          <div className="w-full relative z-20 perspective-1000 mt-8 max-w-3xl">
            <TiltCard className="glass-advanced holographic-border rounded-2xl p-1 overflow-hidden shadow-2xl shadow-primary/10 group lock-on-hover">
              <div className="noise-overlay rounded-2xl"></div>
              <div className="relative z-10">
              {/* Fake Window Header */}
              <div className="flex items-center gap-2 px-4 py-3 border-b border-outline-variant/10 bg-surface/20">
                <div className="w-3 h-3 rounded-full bg-outline-variant/50"></div>
                <div className="w-3 h-3 rounded-full bg-outline-variant/50"></div>
                <div className="w-3 h-3 rounded-full bg-outline-variant/50"></div>
                <div className="ml-auto text-xs font-label text-on-surface-variant/50 font-medium">Secure Session</div>
              </div>
              
              {/* Chat Interface */}
              <div style={{ transform: "translateZ(20px)" }} className="p-6 flex flex-col gap-6 bg-surface-container-low/30 min-h-[320px] text-left">
                {/* User Message */}
                <div className="flex items-start gap-4 self-end max-w-[85%]">
                  <div className="bg-surface-variant/40 border border-outline-variant/20 rounded-2xl rounded-tr-sm p-4 text-base font-body text-on-surface backdrop-blur-sm relative overflow-hidden lock-on-hover cursor-default">
                    Explain this concept using my notes on neural networks.
                  </div>
                  <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center shrink-0 border border-on-secondary-container/20 lock-on-hover cursor-default">
                    <img src="https://ui-avatars.com/api/?name=User&background=571bc1&color=fff" className="w-full h-full rounded-full" alt="User" />
                  </div>
                </div>

                {/* AI Response */}
                <div className="flex items-start gap-4 max-w-[90%]">
                  <div className="w-8 h-8 rounded-full overflow-hidden shrink-0 shadow-lg shadow-primary/20 relative lock-on-hover cursor-default">
                    <div className="absolute inset-0 rounded-full border border-white/20 z-10 pointer-events-none"></div>
                    <img alt="NYRA AI" className="w-full h-full object-cover" src="/logo.webp" />
                  </div>
                  <div className="flex flex-col gap-3 w-full">
                    <div className="text-base font-body text-on-surface/90 leading-relaxed lock-on-hover p-2 rounded-lg cursor-default border border-transparent">
                      Based on your <span className="text-primary font-medium">ML_Notes.pdf</span>, the concept is structured around gradient descent optimization.
                    </div>
                    {/* Knowledge Chip */}
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-tertiary-container/20 border border-tertiary/30 text-tertiary-fixed font-label text-xs w-fit lock-on-hover cursor-pointer font-semibold">
                      <Database className="w-[14px] h-[14px]" />
                      <span>3 Sources Retrieved</span>
                      <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse ml-1"></span>
                    </div>
                    {/* Response Data visualization abstract */}
                    <div className="h-16 w-full rounded-lg bg-surface/40 border border-outline-variant/10 mt-2 overflow-hidden relative opacity-70 lock-on-hover cursor-default">
                      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik0wLDUwIFExMDAsMTAgMjAwLDUwIFQ0MDAsNTAgVDYwMCw1MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNDk0YmQ2IiBzdHJva2Utd2lkdGg9IjIiIG9wYWNpdHk9IjAuNSIvPjwvc3ZnPg==')] bg-repeat-x opacity-30 animate-[slide_10s_linear_infinite]"></div>
                      <div className="absolute left-0 top-0 bottom-0 w-1/3 bg-gradient-to-r from-surface-container-low/80 to-transparent"></div>
                      <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-surface-container-low/80 to-transparent"></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Input area */}
              <div className="p-4 border-t border-outline-variant/10 bg-surface/30 relative text-left">
                <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-primary to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
                <div className="flex items-center gap-3 bg-surface-variant/30 border border-outline-variant/20 rounded-xl px-4 py-3 lock-on-hover cursor-text">
                  <PlusCircle className="text-on-surface-variant cursor-pointer hover:text-primary transition-colors w-6 h-6" />
                  <div className="h-5 w-px bg-outline-variant/30"></div>
                  <span className="text-on-surface-variant/50 font-body text-base flex-1">Ask NYRA anything...</span>
                  <Mic className="text-primary bg-primary/10 rounded-md p-1 cursor-pointer hover:bg-primary/20 transition-colors w-8 h-8" />
                </div>
              </div>
              </div>
            </TiltCard>
          </div>
        </div>
      </main>

      {/* Subtle Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-50 z-20 lock-on-hover p-2 rounded-lg cursor-pointer animate-glide-in">
        <span className="text-xs font-label font-semibold uppercase tracking-widest text-on-surface-variant">Discover</span>
        <div className="w-px h-12 bg-gradient-to-b from-on-surface-variant to-transparent animate-[pulse_2s_ease-in-out_infinite]"></div>
      </div>
    </div>
  );
};

export default Welcome;
