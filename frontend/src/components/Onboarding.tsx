import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import Background from './Background';
import TiltCard from './common/TiltCard';

const AVATARS = [
  { id: 'hulk', name: 'Hulk', url: '/avatars/hulk.jpg' },
  { id: 'wolverine', name: 'Wolverine', url: '/avatars/wolverine.jpg', objectPosition: 'center 15%' },
  { id: 'blackwidow', name: 'Black Widow', url: '/avatars/blackwidow.jpg' },
  { id: 'doctorstrange', name: 'Doctor Strange', url: '/avatars/doctorstrange.jpg' },
  { id: 'blackpanther', name: 'Black Panther', url: '/avatars/blackpanther.jpg' },
  { id: 'captainmarvel', name: 'Captain Marvel', url: '/avatars/captainmarvel.jpg', objectPosition: 'top center' },
  { id: 'hawkeye', name: 'Hawkeye', url: '/avatars/hawkeye.jpg' },
  { id: 'spiderman', name: 'Spider-Man', url: '/avatars/spiderman.jpg' },
  { id: 'ironman', name: 'Iron Man', url: '/avatars/ironman.jpg' },
  { id: 'captainamerica', name: 'Captain America', url: '/avatars/captainamerica.jpg', objectPosition: 'top center' },
  { id: 'thor', name: 'Thor', url: '/avatars/thor.jpg', objectPosition: 'top center' },
  { id: 'scarletwitch', name: 'Scarlet Witch', url: '/avatars/scarletwitch.jpg' },
  { id: 'loki', name: 'Loki', url: '/avatars/loki.jpg' },
  { id: 'thanos', name: 'Thanos', url: '/avatars/thanos.jpg', objectPosition: 'top center' },
  { id: 'deadpool', name: 'Deadpool', url: '/avatars/deadpool.jpg' },
  { id: 'starlord', name: 'Star-Lord', url: '/avatars/starlord.jpg' },
  { id: 'groot', name: 'Groot', url: '/avatars/groot.jpg' },
  { id: 'rocketraccoon', name: 'Rocket Raccoon', url: '/avatars/rocketraccoon.jpg' },
  { id: 'magneto', name: 'Magneto', url: '/avatars/magneto.jpg', objectPosition: 'center 20%' },
  { id: 'venom', name: 'Venom', url: '/avatars/venom.jpg', objectPosition: 'center 15%' }
];

const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const { user, updateUser } = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [selectedAvatar, setSelectedAvatar] = useState(AVATARS[0].url);
  const [loading, setLoading] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const scrollLeft = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: -300, behavior: 'smooth' });
    }
  };

  const scrollRight = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: 300, behavior: 'smooth' });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName.trim() || !selectedAvatar) return;

    setLoading(true);
    try {
      const res = await api.put('/api/auth/profile', {
        display_name: displayName,
        avatar_url: selectedAvatar
      });
      
      updateUser({
        display_name: res.data.display_name,
        avatar_url: res.data.avatar_url
      });

      navigate('/dashboard');
    } catch (err) {
      console.error("Failed to update profile", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dark bg-background text-on-background min-h-screen font-body w-full flex items-center justify-center p-4 relative overflow-hidden">
      <Background />
      
      <TiltCard className="w-full max-w-4xl relative z-10">
        <div className="glass-panel w-full rounded-2xl p-8 lg:p-12 flex flex-col gap-8">
          
          <div className="text-center space-y-2">
            <h1 className="font-display text-4xl font-bold text-on-surface">Choose Your Identity</h1>
            <p className="text-on-surface-variant">Select your avatar and enter a display name to continue.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-10">
            
            {/* Avatar Selection (Horizontal Scrolling Carousel) */}
            <div className="space-y-4">
              <label className="block text-sm font-label uppercase tracking-wider text-on-surface-variant font-semibold text-center">
                Select Avatar
              </label>
              <div className="relative w-full border border-white/5 rounded-xl bg-black/10 p-2">
                <div 
                  className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-y-6 gap-x-4 w-full max-h-[320px] overflow-y-auto px-2 py-4"
                  style={{ scrollbarWidth: 'thin' }}
                >
                  {AVATARS.map((avatar) => {
                    const isSelected = selectedAvatar === avatar.url;
                    return (
                      <motion.div
                        key={avatar.id}
                        animate={{
                          scale: isSelected ? 1.05 : 0.95,
                          opacity: isSelected ? 1 : 0.6,
                        }}
                        transition={{ type: "spring", stiffness: 300, damping: 20 }}
                        onClick={() => setSelectedAvatar(avatar.url)}
                        className="flex flex-col items-center gap-3 cursor-pointer"
                      >
                        <div 
                          className={`relative rounded-full overflow-hidden shadow-lg transition-all duration-300 ${
                            isSelected ? 'border-2 border-primary shadow-[0_0_15px_rgba(var(--primary),0.6)]' : 'border-2 border-transparent hover:opacity-80'
                          }`}
                          style={{ width: '80px', height: '80px' }}
                        >
                          <img 
                            src={avatar.url} 
                            alt={avatar.name} 
                            className="w-full h-full object-cover scale-[1.3] translate-y-1 contrast-125 saturate-150 sepia-[.15]"
                            style={{ 
                              objectPosition: (avatar as any).objectPosition || 'center'
                            }}
                          />
                        </div>
                        <p className={`text-xs text-center font-bold tracking-wide transition-colors duration-300 ${isSelected ? 'text-primary' : 'text-on-surface-variant'}`}>
                          {avatar.name}
                        </p>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Display Name Input */}
            <div className="space-y-4 max-w-md mx-auto">
              <label className="block text-sm font-label uppercase tracking-wider text-on-surface-variant font-semibold text-center">
                Display Name
              </label>
              <input 
                type="text" 
                required
                placeholder="Enter your username..."
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full bg-surface/50 border border-on-surface/10 rounded-xl px-4 py-3 text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-center text-lg font-bold"
              />
            </div>

            <div className="flex justify-center pt-4">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                type="submit"
                disabled={loading || !displayName.trim()}
                className="comic-btn px-10 py-4 text-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? 'SAVING...' : 'ENTER MULTIVERSE'}
              </motion.button>
            </div>
          </form>

        </div>
      </TiltCard>
    </div>
  );
};

export default Onboarding;
