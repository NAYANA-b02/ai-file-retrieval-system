import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Sparkles, 
  Lock, 
  User, 
  AlertCircle, 
  ArrowRight, 
  Loader2, 
  Search, 
  FileText, 
  SlidersHorizontal, 
  Bot 
} from 'lucide-react';

export default function LoginPage() {
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!usernameOrEmail.trim() || !password) {
      setLocalError('Please enter both username/email and password.');
      return;
    }

    setSubmitting(true);
    setLocalError('');
    try {
      await login(usernameOrEmail.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setLocalError(err.message || 'Login failed. Check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#F8F7FC] text-[#334155]">
      {/* Left Visual Area (Desktop Split) */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-[#FAF8FF] via-[#EDE9FE]/50 to-[#EFF6FF] border-r border-[#E2E8F0] p-12 flex-col justify-between relative overflow-hidden">
        {/* Soft background glow circles */}
        <div className="absolute -top-20 -left-20 w-80 h-80 rounded-full bg-[#EDE9FE] blur-3xl opacity-70 pointer-events-none" />
        <div className="absolute -bottom-20 -right-20 w-80 h-80 rounded-full bg-[#BFDBFE] blur-3xl opacity-50 pointer-events-none" />

        <div className="relative z-10">
          <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-white border border-[#E2E8F0] text-[#7C3AED] shadow-subtle mb-6">
            <Sparkles className="w-4 h-4 text-[#A78BFA]" />
            <span className="text-xs font-bold tracking-wide uppercase">AI File Retrieval System</span>
          </div>

          <h1 className="text-3xl xl:text-4xl font-extrabold text-slate-800 tracking-tight leading-snug">
            Search your files.<br />
            Understand your documents.<br />
            <span className="text-[#7C3AED]">Get grounded answers.</span>
          </h1>

          <p className="text-sm text-slate-600 mt-4 max-w-md leading-relaxed">
            A private document intelligence vault with automated OCR, dense semantic embeddings, hybrid keyword search, and strictly grounded citations.
          </p>
        </div>

        {/* Feature Highlights Grid */}
        <div className="relative z-10 grid grid-cols-2 gap-3.5 my-8">
          <div className="p-4 rounded-2xl bg-white/80 backdrop-blur-sm border border-[#E2E8F0] shadow-subtle">
            <div className="w-8 h-8 rounded-xl bg-[#EDE9FE] text-[#7C3AED] flex items-center justify-center mb-2.5">
              <Search className="w-4 h-4" />
            </div>
            <h2 className="text-xs font-bold text-slate-800">Semantic Search</h2>
            <p className="text-[11px] text-slate-500 mt-1 leading-snug">
              FastEmbed BGE-small dense vector similarity across all chunks.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-white/80 backdrop-blur-sm border border-[#E2E8F0] shadow-subtle">
            <div className="w-8 h-8 rounded-xl bg-[#F0FDF4] text-[#16A34A] flex items-center justify-center mb-2.5">
              <FileText className="w-4 h-4" />
            </div>
            <h2 className="text-xs font-bold text-slate-800">Automated OCR</h2>
            <p className="text-[11px] text-slate-500 mt-1 leading-snug">
              PyMuPDF & Tesseract text extraction for PDFs, DOCX, & images.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-white/80 backdrop-blur-sm border border-[#E2E8F0] shadow-subtle">
            <div className="w-8 h-8 rounded-xl bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center mb-2.5">
              <SlidersHorizontal className="w-4 h-4" />
            </div>
            <h2 className="text-xs font-bold text-slate-800">Hybrid Retrieval</h2>
            <p className="text-[11px] text-slate-500 mt-1 leading-snug">
              Combines semantic concepts with exact PostgreSQL full-text search.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-white/80 backdrop-blur-sm border border-[#E2E8F0] shadow-subtle">
            <div className="w-8 h-8 rounded-xl bg-[#FFF7ED] text-[#EA580C] flex items-center justify-center mb-2.5">
              <Bot className="w-4 h-4" />
            </div>
            <h2 className="text-xs font-bold text-slate-800">Grounded RAG</h2>
            <p className="text-[11px] text-slate-500 mt-1 leading-snug">
              Answers backed by verifiable document citations.
            </p>
          </div>
        </div>

        {/* Security badge */}
        <div className="relative z-10 flex items-center gap-2 text-xs text-slate-500">
          <span className="w-2 h-2 rounded-full bg-[#16A34A]" />
          <span>Server-side HttpOnly session cookies & user-isolated storage.</span>
        </div>
      </div>

      {/* Right Side: Authentication Form Card */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md space-y-6">
          {/* Mobile Brand Header */}
          <div className="text-center lg:hidden">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-[#EDE9FE] text-[#7C3AED] mb-3 shadow-subtle">
              <Sparkles className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-bold text-slate-800">AI File Retrieval</h1>
            <p className="text-xs text-slate-500 mt-1">
              Search your files. Understand your documents.
            </p>
          </div>

          {/* Login Card */}
          <div className="bg-white border border-[#E2E8F0] rounded-3xl p-7 sm:p-9 shadow-card">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-slate-800 tracking-tight">Sign In</h2>
              <p className="text-xs text-slate-500 mt-1">
                Enter your account credentials to access your document vault
              </p>
            </div>

            {localError && (
              <div className="mb-5 p-3.5 rounded-2xl bg-[#FFF1F2] border border-[#FDA4AF] text-[#9F1239] text-xs flex items-center gap-2.5">
                <AlertCircle className="w-4 h-4 shrink-0 text-[#E11D48]" />
                <span>{localError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Username or Email
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={usernameOrEmail}
                    onChange={(e) => setUsernameOrEmail(e.target.value)}
                    placeholder="e.g. johndoe or john@example.com"
                    className="w-full pl-10 pr-4 py-2.5 bg-[#F8F7FC] border border-[#E2E8F0] rounded-xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#A78BFA] focus:ring-2 focus:ring-[#A78BFA]/20 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-2.5 bg-[#F8F7FC] border border-[#E2E8F0] rounded-xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#A78BFA] focus:ring-2 focus:ring-[#A78BFA]/20 transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full mt-3 py-3 px-4 bg-[#A78BFA] hover:bg-[#8B5CF6] text-white rounded-2xl text-xs sm:text-sm font-bold shadow-subtle hover:shadow-card transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 pt-5 border-t border-slate-100 text-center">
              <p className="text-xs text-slate-500">
                Don't have an account?{' '}
                <Link to="/register" className="text-[#7C3AED] hover:underline font-bold transition">
                  Create an account
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
