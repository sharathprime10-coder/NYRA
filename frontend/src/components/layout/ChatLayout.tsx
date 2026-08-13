import React, { useEffect, useRef } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import FluidBackground from '../common/FluidBackground';

interface ChatLayoutProps {
  children: React.ReactNode;
}

const ChatLayout: React.FC<ChatLayoutProps> = ({ children }) => {
  const bgRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let animationFrameId: number;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      targetX = (e.clientX / window.innerWidth - 0.5) * 30;
      targetY = (e.clientY / window.innerHeight - 0.5) * 30;
    };

    const animateParallax = () => {
      currentX += (targetX - currentX) * 0.1;
      currentY += (targetY - currentY) * 0.1;

      if (bgRef.current) {
        bgRef.current.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) scale(1.05)`;
      }
      animationFrameId = requestAnimationFrame(animateParallax);
    };

    document.addEventListener('mousemove', handleMouseMove);
    animateParallax();

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="dark bg-background text-on-background antialiased font-body h-screen flex overflow-hidden">
      {/* Background Artwork */}
      <FluidBackground />
      
      <Header />
      <Sidebar />
      
      {/* Main Content Area */}
      <main className="flex-1 h-full w-full md:ml-[280px] pt-16 flex justify-center relative overflow-hidden page-transition">
        {children}
      </main>
    </div>
  );
};

export default ChatLayout;
