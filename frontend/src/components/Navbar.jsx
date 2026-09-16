import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Menu, LogOut, Settings, Sparkles } from 'lucide-react';
import api from '../api/client';

export default function Navbar({ onMenuToggle, onOpenSettings }) {
  const { user, logout } = useAuth();
  const [systemHealthy, setSystemHealthy] = useState(true);

  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      try {
        const res = await api.get('/health');
        if (active) {
          setSystemHealthy(res.data?.status === 'healthy');
        }
      } catch {
        if (active) setSystemHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="h-16 border-b border-[#E2E8F0] bg-white/80 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Left side: Mobile menu toggle + system indicator */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F8F7FC] border border-[#E2E8F0]">
          <span className={`w-2 h-2 rounded-full ${systemHealthy ? 'bg-[#16A34A] animate-pulse' : 'bg-[#E11D48]'}`} />
          <span className="text-[11px] font-semibold text-slate-600">
            {systemHealthy ? 'API Active' : 'API Offline'}
          </span>
        </div>
      </div>

      {/* Right side: User summary & quick actions */}
      <div className="flex items-center gap-3">
        {user && (
          <div className="flex items-center gap-3 pl-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-[#EDE9FE] text-[#7C3AED] flex items-center justify-center font-bold text-xs">
                {user.username ? user.username.slice(0, 2).toUpperCase() : 'U'}
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-xs font-bold text-slate-800 leading-tight">{user.username}</p>
                <p className="text-[11px] text-slate-500 truncate max-w-[140px]">{user.email}</p>
              </div>
            </div>

            <button
              onClick={onOpenSettings}
              className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition"
              title="System Settings"
              aria-label="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            <button
              onClick={logout}
              className="p-2 rounded-xl text-slate-400 hover:text-[#E11D48] hover:bg-[#FFF1F2] transition"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
