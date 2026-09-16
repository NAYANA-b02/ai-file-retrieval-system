import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import { 
  FolderOpen, 
  CheckCircle2, 
  Clock, 
  Database, 
  UploadCloud, 
  Search, 
  Bot, 
  FileText, 
  Sparkles, 
  ArrowRight,
  Loader2,
  HardDrive,
  Eye,
  AlertCircle
} from 'lucide-react';
import FilePreviewModal from '../components/FilePreviewModal';

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quickQuery, setQuickQuery] = useState('');

  // File Preview Modal
  const [previewFile, setPreviewFile] = useState(null);

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

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const totalFiles = files.length;
  const processedFiles = files.filter((f) => f.processing_status === 'completed').length;
  const processingFiles = files.filter((f) => f.processing_status === 'processing' || f.processing_status === 'uploaded').length;
  const totalBytes = files.reduce((acc, f) => acc + (f.size || 0), 0);

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const handleQuickSearch = (e) => {
    e.preventDefault();
    if (quickQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(quickQuery.trim())}`);
    } else {
      navigate('/search');
    }
  };

  return (
    <div className="space-y-7">
      {/* Header Greeting & Subtitle */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight">
            {getGreeting()}, {user?.username || 'User'}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Search, manage and understand your documents.
          </p>
        </div>

        <Link
          to="/upload"
          className="self-start md:self-auto inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-[#A78BFA] hover:bg-[#8B5CF6] text-white text-xs font-bold shadow-subtle hover:shadow-card transition"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Upload File</span>
        </Link>
      </div>

      {/* Prominent Search Bar */}
      <div className="bg-white border border-[#E2E8F0] rounded-3xl p-3 sm:p-4 shadow-subtle">
        <form onSubmit={handleQuickSearch} className="relative flex items-center">
          <div className="absolute left-4 text-slate-400">
            <Search className="w-5 h-5 text-[#A78BFA]" />
          </div>
          <input
            type="text"
            value={quickQuery}
            onChange={(e) => setQuickQuery(e.target.value)}
            placeholder="Search across all your documents (semantic concepts, keywords, or topics)..."
            className="w-full pl-12 pr-28 py-3 bg-[#F8F7FC] border border-transparent rounded-2xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-[#A78BFA] focus:ring-2 focus:ring-[#A78BFA]/20 transition"
          />
          <button
            type="submit"
            className="absolute right-2 top-2 bottom-2 px-4 sm:px-5 bg-white border border-[#E2E8F0] hover:bg-[#FAF8FF] hover:border-[#A78BFA] text-[#7C3AED] rounded-xl text-xs font-bold shadow-subtle transition flex items-center gap-1.5"
          >
            <span>Search</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-[#FFF1F2] border border-[#FDA4AF] text-[#9F1239] text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-[#E11D48]" />
          <span>{error}</span>
        </div>
      )}

      {/* Statistics Cards (Pastel Icons) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Files - Lavender */}
        <div className="bg-white border border-[#E2E8F0] rounded-3xl p-5 shadow-subtle hover:shadow-card transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Total Files</span>
            <div className="w-10 h-10 rounded-2xl bg-[#EDE9FE] text-[#7C3AED] flex items-center justify-center">
              <FolderOpen className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-800 mt-3">
            {loading ? '...' : totalFiles}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Uploaded in private vault</p>
        </div>

        {/* Processed - Mint */}
        <div className="bg-white border border-[#E2E8F0] rounded-3xl p-5 shadow-subtle hover:shadow-card transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Processed</span>
            <div className="w-10 h-10 rounded-2xl bg-[#F0FDF4] text-[#16A34A] flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-800 mt-3">
            {loading ? '...' : processedFiles}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Indexed & ready for search</p>
        </div>

        {/* Processing - Peach */}
        <div className="bg-white border border-[#E2E8F0] rounded-3xl p-5 shadow-subtle hover:shadow-card transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Processing</span>
            <div className="w-10 h-10 rounded-2xl bg-[#FFF7ED] text-[#EA580C] flex items-center justify-center">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-800 mt-3">
            {loading ? '...' : processingFiles}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Extracting or chunking</p>
        </div>

        {/* Storage Used - Soft Blue */}
        <div className="bg-white border border-[#E2E8F0] rounded-3xl p-5 shadow-subtle hover:shadow-card transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Storage Used</span>
            <div className="w-10 h-10 rounded-2xl bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center">
              <HardDrive className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-800 mt-3">
            {loading ? '...' : formatBytes(totalBytes)}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Encrypted storage usage</p>
        </div>
      </div>

      {/* Quick Actions Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/upload"
          className="group p-6 rounded-3xl bg-white border border-[#E2E8F0] hover:border-[#A78BFA] hover:shadow-card transition flex flex-col justify-between"
        >
          <div>
            <div className="w-11 h-11 rounded-2xl bg-[#EDE9FE] text-[#7C3AED] flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
              <UploadCloud className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-slate-800">Upload File</h2>
            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
              Add PDF, DOCX, TXT, or images with automated OCR extraction and vector embedding.
            </p>
          </div>
          <span className="text-xs text-[#7C3AED] font-bold mt-4 inline-flex items-center gap-1 group-hover:translate-x-1 transition-transform">
            Go to Upload &rarr;
          </span>
        </Link>

        <Link
          to="/search"
          className="group p-6 rounded-3xl bg-white border border-[#E2E8F0] hover:border-[#BFDBFE] hover:shadow-card transition flex flex-col justify-between"
        >
          <div>
            <div className="w-11 h-11 rounded-2xl bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
              <Search className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-slate-800">Search Documents</h2>
            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
              Find exact information with Semantic, Keyword, or Hybrid reciprocal rank fusion.
            </p>
          </div>
          <span className="text-xs text-[#2563EB] font-bold mt-4 inline-flex items-center gap-1 group-hover:translate-x-1 transition-transform">
            Open Search &rarr;
          </span>
        </Link>

        <Link
          to="/rag"
          className="group p-6 rounded-3xl bg-white border border-[#E2E8F0] hover:border-[#BBF7D0] hover:shadow-card transition flex flex-col justify-between"
        >
          <div>
            <div className="w-11 h-11 rounded-2xl bg-[#F0FDF4] text-[#16A34A] flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
              <Bot className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-slate-800">Ask AI</h2>
            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
              Ask natural language questions and get verifiable answers grounded in your files.
            </p>
          </div>
          <span className="text-xs text-[#16A34A] font-bold mt-4 inline-flex items-center gap-1 group-hover:translate-x-1 transition-transform">
            Start Asking &rarr;
          </span>
        </Link>
      </div>

      {/* Recent Files Section */}
      <div className="bg-white border border-[#E2E8F0] rounded-3xl p-6 shadow-subtle">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#FAF8FF] border border-[#E2E8F0] text-[#7C3AED] flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-slate-800">Recent Files</h2>
          </div>
          <Link
            to="/files"
            className="text-xs text-[#7C3AED] hover:underline font-bold transition"
          >
            View All Files
          </Link>
        </div>

        {loading ? (
          <div className="py-12 text-center flex flex-col items-center justify-center gap-2">
            <Loader2 className="w-6 h-6 text-[#A78BFA] animate-spin" />
            <p className="text-xs text-slate-400 font-medium">Loading documents...</p>
          </div>
        ) : files.length === 0 ? (
          <div className="py-12 text-center space-y-2">
            <div className="w-12 h-12 rounded-2xl bg-[#F8F7FC] text-slate-400 flex items-center justify-center mx-auto">
              <FolderOpen className="w-6 h-6" />
            </div>
            <p className="text-xs font-bold text-slate-700">No documents yet</p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Upload your first document to start searching and asking questions.
            </p>
            <Link
              to="/upload"
              className="inline-block mt-2 px-4 py-2 rounded-xl bg-[#EDE9FE] text-[#7C3AED] text-xs font-bold hover:bg-[#DDD6FE] transition"
            >
              Upload Document
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-slate-400 border-b border-slate-100">
                  <th className="pb-3 font-semibold">Filename</th>
                  <th className="pb-3 font-semibold">Format</th>
                  <th className="pb-3 font-semibold">Size</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {files.slice(0, 5).map((f) => (
                  <tr key={f.id} className="hover:bg-[#F8F7FC] transition group">
                    <td className="py-3.5 font-semibold text-slate-800 truncate max-w-[200px] sm:max-w-xs">
                      {f.original_filename}
                    </td>
                    <td className="py-3.5">
                      <span className="uppercase font-mono text-[10px] font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">
                        {(f.extension || '').replace('.', '')}
                      </span>
                    </td>
                    <td className="py-3.5 text-slate-500 font-medium">{formatBytes(f.size)}</td>
                    <td className="py-3.5">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                          f.processing_status === 'completed'
                            ? 'bg-[#F0FDF4] text-[#166534] border border-[#BBF7D0]'
                            : f.processing_status === 'failed'
                            ? 'bg-[#FFF1F2] text-[#9F1239] border border-[#FDA4AF]'
                            : 'bg-[#FFF7ED] text-[#9A3412] border border-[#FED7AA]'
                        }`}
                      >
                        {f.processing_status === 'completed' ? 'Processed' : f.processing_status}
                      </span>
                    </td>
                    <td className="py-3.5 text-right">
                      <button
                        onClick={() => setPreviewFile(f)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-[#E2E8F0] bg-white text-slate-600 hover:text-[#7C3AED] hover:border-[#A78BFA] transition font-semibold text-[11px]"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Preview</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* File Preview Modal */}
      {previewFile && (
        <FilePreviewModal
          file={previewFile}
          isOpen={Boolean(previewFile)}
          onClose={() => setPreviewFile(null)}
        />
      )}
    </div>
  );
}
