import React from 'react';

const FluidBackground: React.FC = () => {
  return (
    <div className="fixed inset-0 z-[-1] overflow-hidden bg-surface-container-lowest flex items-center justify-center">
      {/* 
        Animated Black Hole Environment inspired by Reflect.app
      */}
      <div className="relative w-full h-full flex items-center justify-center">
        
        {/* Accretion Disk (Outer Glow) */}
        <div 
          className="absolute w-[120vw] h-[40vh] md:w-[80vw] md:h-[30vh] rounded-[100%] mix-blend-screen filter blur-[40px] opacity-60 animate-spin-slow"
          style={{
            background: 'conic-gradient(from 0deg, rgba(87,27,193,0) 0%, rgba(47,217,244,0.8) 25%, rgba(192,193,255,0.4) 50%, rgba(87,27,193,0.8) 75%, rgba(87,27,193,0) 100%)',
            transform: 'rotateX(75deg)',
          }}
        />

        {/* Accretion Disk (Inner Bright Ring) */}
        <div 
          className="absolute w-[80vw] h-[25vh] md:w-[50vw] md:h-[15vh] rounded-[100%] mix-blend-screen filter blur-[15px] opacity-90 animate-spin-fast"
          style={{
            background: 'conic-gradient(from 180deg, rgba(192,193,255,0) 0%, rgba(255,255,255,0.9) 25%, rgba(47,217,244,0.6) 50%, rgba(255,255,255,0.9) 75%, rgba(192,193,255,0) 100%)',
            transform: 'rotateX(75deg)',
          }}
        />

        {/* The Event Horizon (The Black Hole itself) */}
        <div 
          className="absolute w-[40vw] h-[40vw] md:w-[25vw] md:h-[25vw] rounded-full bg-background z-10 shadow-[0_0_100px_40px_rgba(17,19,29,1)]"
          style={{
            transform: 'translateY(-10%)',
          }}
        />

        {/* Top Arc Glow (Light bending over the top) */}
        <div 
          className="absolute w-[45vw] h-[25vw] md:w-[28vw] md:h-[15vw] rounded-t-full border-t-[12px] border-white filter blur-[12px] opacity-60 z-20 mix-blend-screen"
          style={{
            transform: 'translateY(-30%)',
          }}
        />
        
        {/* Deep ambient background glow behind everything */}
        <div 
          className="absolute w-[100vw] h-[100vh] rounded-full bg-primary/20 blur-[150px] mix-blend-screen opacity-30 z-0"
        />

      </div>
      
      {/* Heavy noise overlay for the entire background to give it that premium texture */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-[0.03] z-30" 
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
        }}
      />
    </div>
  );
};

export default FluidBackground;
