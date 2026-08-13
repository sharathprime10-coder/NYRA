import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Background from './Background';
import { Mail, Lock, Eye, ArrowRight } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import TiltCard from './common/TiltCard';
import api from '../api/client';

const quotes = [
  "The more I love humanity in general, the less I love man in particular.",
  "If there is no God, then everything is permitted.",
  "The mystery of human existence lies not in just staying alive, but in finding something to live for.",
  "Hell is the suffering of being unable to love."
];

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [quoteIndex, setQuoteIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setQuoteIndex((prev) => (prev + 1) % quotes.length);
    }, 10000); // 10 seconds interval
    return () => clearInterval(interval);
  }, []);

  const handleGoogleSuccess = async (credentialResponse: any) => {
    try {
      setError(null);
      const res = await api.post('/api/auth/google', {
        credential: credentialResponse.credential,
      });
      
      login(res.data.access_token, {
        id: res.data.user_id,
        username: res.data.username,
        display_name: res.data.display_name,
        avatar_url: res.data.avatar_url
      });
      
      if (!res.data.display_name) {
        navigate('/onboarding');
      } else {
        navigate('/dashboard');
      }
    } catch (err: any) {
      console.error("Login failed:", err);
      const errorMessage = err.response?.data?.detail || err.message || "BACKEND_UNREACHABLE_OR_CORS_ERROR";
      setError(String(errorMessage));
    }
  };
  return (
    <div className="dark bg-background text-on-background min-h-screen font-body w-full h-screen overflow-hidden selection:bg-primary selection:text-on-primary">
      <Background />
      <div className="flex h-screen w-full relative z-10">
        {/* Left Side: Artwork & Branding */}
        <div className="hidden lg:flex w-1/2 relative flex-col justify-between p-[64px]">
          <div className="relative z-10">
            <div className="w-24 h-24 mb-4 rounded-xl overflow-hidden glass-panel flex items-center justify-center p-2">
              <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuB1owtDrGiK0eLLr0TiFNNHaZuvX2WhyFxW8q0XM6csuaJeTvZUOHW-0sv9XITQuO8qC31-UYdvXXHJ7gaCZEpZjyR-U0sH8d4pym7yY3-wHcl2eTjwtjBz1x5MFjsJFCFWK4A3-Ld9s9NLGxYvyrRzudMezd2ptn2NMrhuOrKh-5D_QVEa1bZahSL5bXJ5rAROMZ_3-PFnuR7qt1Lwhm6IkpFVT-AY0--f1jDzEQtr361yI64qWV1DUvOjviMQAKyEkag" alt="NYRA Logo" className="w-full h-full object-contain" />
            </div>
            <p className="font-body text-lg text-on-surface-variant mt-2 max-w-md">Premium Knowledge Assistant. Enter the nexus of infinite data.</p>
          </div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 text-on-surface-variant/60 font-label text-xs uppercase tracking-widest font-semibold">
              <span className="w-8 h-px bg-on-surface-variant/30"></span>
              System Online
            </div>
          </div>
        </div>

        {/* Right Side: Authentication */}
        <div className="w-full lg:w-1/2 flex items-center justify-center p-[20px] lg:p-[64px] relative z-20">
          {/* Mobile Branding (Hidden on Desktop) */}
          <div className="absolute top-8 left-8 lg:hidden">
            <div className="w-16 h-16 rounded-lg overflow-hidden glass-panel flex items-center justify-center p-1.5">
              <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuB0OqKVXHF8cmSgMdKy_a4a4i8v28-zf31elQdXNrSOvB5npHMGcA3j4G8e3L_ZaOAshvHfzoHIYbmXQlZ0sr3nfsKnwQ6j5FrcyK6xhrh0cQ3SIfrRwPrChW82_s7DWMdQHodu7_a-7BHlDxgH3s1XSPRDm9163JClEnUy43pcuqCosUYQLwzJ1EpsP7c7C87T7Cq-a0wlMX6olKgqZIdLorA3BuUtX1EGrMpbIlMKepi8h-S2jVIYtsHCEc1bT4Uq5Yc" alt="NYRA Logo" className="w-full h-full object-contain" />
            </div>
          </div>

          <TiltCard className="w-full max-w-md">
            <div className="glass-panel w-full rounded-xl p-8 lg:p-10 flex flex-col gap-8 transform-style-preserve-3d">
              <div className="space-y-2" style={{ transform: "translateZ(30px)" }}>
              <div className="w-16 h-16 mb-6 rounded-lg overflow-hidden glass-panel flex items-center justify-center p-1.5 mx-auto lg:mx-0">
                <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuBFGhnK99DHPNTure4Fj01lb9CEBV3Be6ht0VrGxZYOjki4wbW9ilPzRrudp-HI7xj7baypxYBb8rOfMl-epvBjAS0rpEQUSPRAojg52_-qQNjkdbMCgvq_8g6V90Q0PldGdTpNOPF188uez-BLJ1yzVdp8eGOF6DKjIDEPanVJxbWoJgrXDWYvRHxUpe6fbFix_nnxiUp4R2PCenXgwJnGLfoIkObQsSdM01hw92Lv1uokZGX_MDyMhabz0ZGj5tAA-8U" alt="NYRA Logo" className="w-full h-full object-contain" />
              </div>
              <h2 className="font-display text-2xl font-semibold text-on-surface">Login to your workspace</h2>
              <div className="relative h-16 w-full overflow-hidden">
                <AnimatePresence mode="wait">
                  <motion.p
                    key={quoteIndex}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 1 }}
                    className="font-body text-sm text-on-surface-variant absolute inset-0 italic"
                  >
                    "{quotes[quoteIndex]}"
                  </motion.p>
                </AnimatePresence>
              </div>
            </div>

            <div className="flex flex-col gap-6 w-full" style={{ transform: "translateZ(20px)" }}>
              {error && (
                <div className="p-4 bg-error/10 border border-error/20 text-error rounded-lg font-body text-sm text-center">
                  {error}
                </div>
              )}
              
              <div className="flex justify-center w-full">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => {
                    setError("Google authentication failed.");
                  }}
                  useOneTap
                  theme="filled_black"
                  shape="rectangular"
                  size="large"
                  text="signin_with"
                  width="100%"
                />
              </div>
              
            </div>
            </div>
          </TiltCard>
        </div>
      </div>
    </div>
  );
};

export default Login;
