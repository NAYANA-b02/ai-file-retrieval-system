import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import { 
  Files, 
  Database, 
  CheckCircle2, 
  UploadCloud, 
  Search, 
  Bot, 
  Cpu, 
  Shield, 
  Clock, 
  FileText,
  AlertCircle,
  Layers
} from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        setLoading(true);
        const res = await api.get('/files');
        setFiles(res.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchFiles();
  }, []);

  const totalFiles = files.length;
  const completedFiles = files.filter((f) => f.processing_status === 'completed').length;
  const totalChunks = files.reduce((acc, f) => acc + (f.text_chunk_count || 0), 0);
  const totalBytes = files.reduce((acc, f) => acc + (f.size || 0), 0);
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-brand-900/40 via-slate-900/80 to-slate-900/40 border border-brand-500/20 p-6 sm:p-8">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-semibold mb-3">
            <Shield className="w-3.5 h-3.5" />
            <span>Secure Vault & RAG Engine</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Hello, {user?.username}
          </h1>
          <p className="text-slate-300 text-xs sm:text-sm mt-2 leading-relaxed">
            Your documents are processed through automated OCR text extraction, chunked, embedded with <code className="text-brand-300 bg-brand-950/60 px-1.5 py-0.5 rounded text-[11px]">all-MiniLM-L6-v2</code>, and indexed for fast hybrid search and grounded RAG responses.
          </p>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Documents</span>
            <div className="p-2 rounded-xl bg-brand-500/10 text-brand-400">
              <Files className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-white mt-3">{loading ? '...' : totalFiles}</p>
          <p className="text-[11px] text-slate-500 mt-1">Uploaded to your private vault</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Vector Chunks</span>
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-white mt-3">{loading ? '...' : totalChunks}</p>
          <p className="text-[11px] text-slate-500 mt-1">Embedded & indexed for retrieval</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Processed Files</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-white mt-3">{loading ? '...' : completedFiles}</p>
          <p className="text-[11px] text-slate-500 mt-1">Extraction & OCR completed</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Storage Used</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <Database className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-white mt-3">{loading ? '...' : formatBytes(totalBytes)}</p>
          <p className="text-[11px] text-slate-500 mt-1">Encrypted on server storage</p>
        </div>
      </div>

      {/* Action Panels */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/upload"
          className="group p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-brand-500/40 hover:bg-slate-900 transition flex flex-col justify-between"
        >
          <div>
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <UploadCloud className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-white">Upload New Files</h3>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Upload PDF, DOCX, TXT, or scanned images for OCR and automated vector embedding.
            </p>
          </div>
          <span className="text-xs text-brand-400 font-medium mt-4 inline-flex items-center gap-1 group-hover:translate-x-1 transition-transform">
            Go to Upload &rarr;
          </span>
        </Link>

        <Link
          to="/search"
          className="group p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-indigo-500/40 hover:bg-slate-900 transition flex flex-col justify-between"
        >
          <div>
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Search className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-white">Intelligent Search</h3>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Search by natural language semantic concepts, exact keywords, or balanced hybrid scoring.
            </p>
          </div>
          <span className="text-xs text-indigo-400 font-medium mt-4 inline-flex items-center gap-1 group-hover:translate-x-1 transition-transform">
            Open Search Engine &rarr;
          </span>
        </Link>

        <Link
          to="/rag"
          className="group p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-emerald-500/40 hover:bg-slate-900 transition flex flex-col justify-between"
        >
          <div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Bot className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-white">Ask AI (RAG)</h3>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Ask questions directly against your uploaded documents with verifiable source citations.
            </p>
          </div>
          <span className="text-xs text-emerald-400 font-medium mt-4 inline-flex items-center gap-1 group-hover:translate-x-1 transition-transform">
            Ask Questions &rarr;
          </span>
        </Link>
      </div>

      {/* System Architecture & Recent Files */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Files Table */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-brand-400" />
              Recent Documents
            </h2>
            <Link to="/files" className="text-xs text-brand-400 hover:text-brand-300 transition font-medium">
              View All
            </Link>
          </div>

          {loading ? (
            <div className="py-8 text-center text-xs text-slate-500">Loading files...</div>
          ) : files.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-xs text-slate-400">No documents uploaded yet.</p>
              <Link to="/upload" className="mt-2 inline-block text-xs text-brand-400 font-semibold hover:underline">
                Upload your first document
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-slate-400 border-b border-slate-800/80">
                    <th className="pb-3 font-medium">Filename</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Chunks</th>
                    <th className="pb-3 font-medium text-right">Uploaded</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {files.slice(0, 5).map((f) => (
                    <tr key={f.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 font-medium text-slate-200 truncate max-w-[200px]">
                        {f.original_filename}
                      </td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            f.processing_status === 'completed'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : f.processing_status === 'failed'
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          }`}
                        >
                          {f.processing_status}
                        </span>
                      </td>
                      <td className="py-3 text-slate-400">{f.text_chunk_count || 0}</td>
                      <td className="py-3 text-slate-500 text-right">
                        {new Date(f.uploaded_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Backend Pipeline Specs */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm space-y-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-400" />
            Active AI Pipeline
          </h2>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1">
              <span className="text-[11px] text-slate-400 font-medium">Embedding Engine</span>
              <p className="font-semibold text-slate-200">all-MiniLM-L6-v2 (384-d)</p>
              <p className="text-[10px] text-slate-500">Dense semantic vector similarity</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1">
              <span className="text-[11px] text-slate-400 font-medium">Text & OCR Service</span>
              <p className="font-semibold text-slate-200">Tesseract OCR & PyMuPDF</p>
              <p className="text-[10px] text-slate-500">PDF, DOCX, TXT, PNG, JPG support</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1">
              <span className="text-[11px] text-slate-400 font-medium">Generation Model</span>
              <p className="font-semibold text-slate-200">Llama 3.2 3B (Local Ollama)</p>
              <p className="text-[10px] text-slate-500">Strictly grounded citation answering</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1">
              <span className="text-[11px] text-slate-400 font-medium">Security & Audit</span>
              <p className="font-semibold text-slate-200">Server Session Isolation</p>
              <p className="text-[10px] text-slate-500">All queries & uploads logged to audit_logs</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
