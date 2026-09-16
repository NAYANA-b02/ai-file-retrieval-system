import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FolderOpen, 
  UploadCloud, 
  Search, 
  Bot, 
  Settings, 
  LogOut, 
  X, 
  Sparkles 
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'My Files', path: '/files', icon: FolderOpen },
  { name: 'Upload', path: '/upload', icon: UploadCloud },
  { name: 'Search', path: '/search', icon: Search },
  { name: 'Ask AI', path: '/rag', icon: Bot },
];

export default function Sidebar({ isOpen, onClose, onOpenSettings }) {
  const { user, logout } = useAuth();

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/30 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed lg:static top-0 left-0 bottom-0 w-64 bg-white border-r border-[#E2E8F0] p-5 flex flex-col justify-between z-50 transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div>
          {/* Brand Header */}
          <div className="flex items-center justify-between pb-6 mb-6 border-b border-[#E2E8F0]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-[#EDE9FE] text-[#7C3AED] flex items-center justify-center shadow-subtle">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-sm font-bold text-slate-800 tracking-tight leading-none">
                  AI File Retrieval
                </h1>
                <p className="text-[11px] text-slate-500 font-medium mt-1">
                  Document Vault & RAG
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
              aria-label="Close sidebar"
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
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-xs font-semibold transition-all duration-150 ${
                    isActive
                      ? 'bg-[#EDE9FE] text-[#6D28D9] shadow-subtle'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-[#F8F7FC]'
                  }`
                }
              >
                <item.icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* User Info & Footer Actions */}
        <div className="pt-4 border-t border-[#E2E8F0] space-y-3">
          {/* User Profile Area */}
          {user && (
            <div className="p-3 rounded-2xl bg-[#F8F7FC] border border-[#E2E8F0] flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-[#DDD6FE] text-[#6D28D9] flex items-center justify-center font-bold text-xs shrink-0">
                {user.username ? user.username.slice(0, 2).toUpperCase() : 'U'}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-slate-800 truncate">{user.username}</p>
                <p className="text-[10px] text-slate-500 truncate">{user.email}</p>
              </div>
            </div>
          )}

          {/* Settings & Logout Buttons */}
          <div className="space-y-1">
            <button
              onClick={() => {
                if (onClose) onClose();
                if (onOpenSettings) onOpenSettings();
              }}
              className="w-full flex items-center gap-3 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-[#F8F7FC] transition"
            >
              <Settings className="w-4 h-4 text-slate-500" />
              <span>Settings</span>
            </button>

            <button
              onClick={logout}
              className="w-full flex items-center gap-3 px-3.5 py-2 rounded-xl text-xs font-semibold text-[#9F1239] hover:bg-[#FFF1F2] transition"
            >
              <LogOut className="w-4 h-4 text-[#FDA4AF]" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
