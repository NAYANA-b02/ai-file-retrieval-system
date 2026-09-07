import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, User, Activity, Menu } from 'lucide-react';
import api from '../api/client';

export default function Navbar({ onMenuToggle }) {
  const { user, logout } = useAuth();
  const [systemHealthy, setSystemHealthy] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await api.get('/health');
        if (res.data?.status === 'healthy') {
          setSystemHealthy(true);
        }
      } catch {
        setSystemHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-medium text-slate-400 hidden sm:inline-block">
            {systemHealthy ? 'Core API Online' : 'Core API Offline'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3 pl-4 border-l border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-brand-600/30 border border-brand-500/40 text-brand-300 flex items-center justify-center font-semibold text-xs">
                {user.username.slice(0, 2).toUpperCase()}
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-xs font-medium text-slate-200">{user.username}</p>
                <p className="text-[11px] text-slate-500 truncate max-w-[140px]">{user.email}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition flex items-center gap-1.5 text-xs font-medium"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden md:inline">Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
