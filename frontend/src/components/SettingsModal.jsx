import React, { useEffect } from 'react';
import { X, ShieldCheck, Sparkles, Database, Cpu, HardDrive } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function SettingsModal({ isOpen, onClose }) {
  const { user } = useAuth();

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-modal-title"
    >
      <div 
        className="bg-white border border-[#E2E8F0] rounded-3xl p-6 sm:p-7 max-w-lg w-full shadow-card animate-fade-in space-y-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#EDE9FE] text-[#7C3AED] flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 id="settings-modal-title" className="text-base font-bold text-slate-800">
                System Preferences & Status
              </h2>
              <p className="text-xs text-slate-500">
                AI File Retrieval System Configuration
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Profile Card */}
        <div className="p-4 rounded-2xl bg-[#FAF8FF] border border-[#EDE9FE] flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-2xl bg-[#DDD6FE] text-[#6D28D9] flex items-center justify-center font-bold text-sm">
            {user?.username ? user.username.slice(0, 2).toUpperCase() : 'US'}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold text-slate-800">{user?.username}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
          <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-[#BBF7D0] text-[#166534]">
            Active Session
          </span>
        </div>

        {/* System Specs List */}
        <div className="space-y-2.5 text-xs">
          <div className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-[#F8F7FC]">
            <div className="flex items-center gap-2.5 text-slate-600">
              <Cpu className="w-4 h-4 text-[#A78BFA]" />
              <span className="font-semibold">Embedding Model</span>
            </div>
            <span className="font-mono text-[11px] text-slate-700 font-semibold bg-white px-2 py-0.5 rounded-md border border-slate-200">
              BAAI/bge-small-en-v1.5
            </span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-[#F8F7FC]">
            <div className="flex items-center gap-2.5 text-slate-600">
              <Sparkles className="w-4 h-4 text-[#A78BFA]" />
              <span className="font-semibold">RAG Generation Provider</span>
            </div>
            <span className="font-mono text-[11px] text-slate-700 font-semibold bg-white px-2 py-0.5 rounded-md border border-slate-200">
              Groq (Prod) / Ollama (Local)
            </span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-[#F8F7FC]">
            <div className="flex items-center gap-2.5 text-slate-600">
              <Database className="w-4 h-4 text-[#A78BFA]" />
              <span className="font-semibold">Database & Vectors</span>
            </div>
            <span className="font-mono text-[11px] text-slate-700 font-semibold bg-white px-2 py-0.5 rounded-md border border-slate-200">
              PostgreSQL + pgvector
            </span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-[#F8F7FC]">
            <div className="flex items-center gap-2.5 text-slate-600">
              <HardDrive className="w-4 h-4 text-[#A78BFA]" />
              <span className="font-semibold">Storage Architecture</span>
            </div>
            <span className="font-mono text-[11px] text-slate-700 font-semibold bg-white px-2 py-0.5 rounded-md border border-slate-200">
              Private Bucket / UUID Path Isolation
            </span>
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#EFF6FF] border border-[#BFDBFE] text-[#1E40AF] text-[11px] leading-relaxed">
          <span className="font-bold block mb-0.5">Strict Privacy & Security:</span>
          Each user's files and vector embeddings are logically segregated. Server filesystem paths and credentials are never transmitted to clients.
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
