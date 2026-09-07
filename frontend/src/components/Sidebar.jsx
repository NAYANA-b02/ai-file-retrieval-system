import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  UploadCloud, 
  Files, 
  Search, 
  Bot, 
  ShieldCheck, 
  X 
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Upload Files', path: '/upload', icon: UploadCloud },
  { name: 'My Files', path: '/files', icon: Files },
  { name: 'Search Engine', path: '/search', icon: Search },
  { name: 'Ask AI (RAG)', path: '/rag', icon: Bot },
];

export default function Sidebar({ isOpen, onClose }) {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed lg:static top-0 left-0 bottom-0 w-64 bg-slate-900/90 border-r border-slate-800/80 p-5 flex flex-col justify-between z-50 transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div>
          {/* Brand Header */}
          <div className="flex items-center justify-between pb-6 mb-6 border-b border-slate-800/80">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
                <ShieldCheck className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-sm font-bold text-slate-100 tracking-tight leading-none">
                  RETRIEVAL AI
                </h1>
                <p className="text-[10px] text-slate-400 font-medium tracking-wider uppercase mt-0.5">
                  OCR • Search • RAG
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 ${
                    isActive
                      ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30 shadow-sm shadow-brand-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <item.icon className="w-4 h-4" />
                <span>{item.name}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Security & System Info Footer */}
        <div className="pt-4 border-t border-slate-800/80">
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="flex items-center justify-between text-slate-300 font-medium">
              <span>Security Level</span>
              <span className="text-emerald-400 font-semibold">Protected</span>
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">
              Isolated user workspaces, chunk-level vectors, and safe RAG grounding.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
