import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { 
  Files, 
  Search, 
  Eye, 
  X, 
  AlertCircle, 
  Layers, 
  Calendar, 
  HardDrive, 
  FileText, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RefreshCw,
  Loader2
} from 'lucide-react';
import { Link } from 'react-router-dom';

export default function FilesPage() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');

  // Drawer / Modal state for file detail inspection
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [fileDetails, setFileDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState(null);

  const fetchFiles = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/files');
      setFiles(res.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const openFileDetails = async (id) => {
    setSelectedFileId(id);
    setLoadingDetails(true);
    setDetailsError(null);
    try {
      const res = await api.get(`/files/${id}`);
      setFileDetails(res.data);
    } catch (err) {
      setDetailsError(err.message);
    } finally {
      setLoadingDetails(false);
    }
  };

  const closeDetails = () => {
    setSelectedFileId(null);
    setFileDetails(null);
    setDetailsError(null);
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const filteredFiles = files.filter((f) =>
    f.original_filename.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">My Documents</h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Browse and inspect all documents stored in your private vault with extracted text and vector chunk status.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={fetchFiles}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition text-xs flex items-center gap-1.5"
            title="Refresh Files"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
          <Link
            to="/upload"
            className="py-2.5 px-4 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-brand-600/20 transition"
          >
            Upload Document
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-sm">
        <div className="relative max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Search by file name..."
            className="w-full pl-9 pr-3.5 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 transition"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Files Table / Grid */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm shadow-xl">
        {loading ? (
          <div className="py-16 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 text-brand-500 animate-spin" />
            <span>Loading documents...</span>
          </div>
        ) : filteredFiles.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-800/80 text-slate-500 flex items-center justify-center mx-auto">
              <Files className="w-6 h-6" />
            </div>
            <p className="text-sm font-medium text-slate-300">No documents found</p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {searchFilter
                ? 'No documents matched your search filter.'
                : 'Your vault is currently empty. Upload files to run OCR, embeddings, and RAG.'}
            </p>
            {!searchFilter && (
              <Link
                to="/upload"
                className="inline-block mt-2 text-xs text-brand-400 hover:text-brand-300 font-semibold"
              >
                Upload your first file &rarr;
              </Link>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-950/60 border-b border-slate-800/90 text-slate-400">
                  <th className="py-3.5 px-4 font-semibold">Document Name</th>
                  <th className="py-3.5 px-4 font-semibold">Format</th>
                  <th className="py-3.5 px-4 font-semibold">Size</th>
                  <th className="py-3.5 px-4 font-semibold">Status</th>
                  <th className="py-3.5 px-4 font-semibold">Chunks</th>
                  <th className="py-3.5 px-4 font-semibold">Uploaded</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filteredFiles.map((file) => (
                  <tr key={file.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4 font-medium text-slate-200">
                      <div className="flex items-center gap-2.5">
                        <FileText className="w-4 h-4 text-brand-400 shrink-0" />
                        <span className="truncate max-w-[200px] sm:max-w-xs">{file.original_filename}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="uppercase text-[11px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                        {file.extension.replace('.', '')}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">{formatBytes(file.size)}</td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold ${
                          file.processing_status === 'completed'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : file.processing_status === 'failed'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}
                      >
                        {file.processing_status === 'completed' && <CheckCircle2 className="w-3 h-3" />}
                        {file.processing_status === 'failed' && <XCircle className="w-3 h-3" />}
                        {file.processing_status === 'uploaded' && <Clock className="w-3 h-3" />}
                        {file.processing_status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <Layers className="w-3.5 h-3.5 text-brand-400" />
                        <span>{file.text_chunk_count || 0}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-500">
                      {new Date(file.uploaded_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => openFileDetails(file.id)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-brand-300 hover:bg-brand-500/10 transition inline-flex items-center gap-1"
                        title="View Extracted Text & Metadata"
                      >
                        <Eye className="w-4 h-4" />
                        <span className="text-[11px] font-medium hidden sm:inline">Preview</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* File Detail Modal / Preview Drawer */}
      {selectedFileId && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <FileText className="w-5 h-5 text-brand-400" />
                <div>
                  <h3 className="text-sm font-semibold text-white truncate max-w-md">
                    {fileDetails ? fileDetails.original_filename : 'Document Details'}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    File ID #{selectedFileId} • Secure Vault Inspection
                  </p>
                </div>
              </div>
              <button
                onClick={closeDetails}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content Body */}
            <div className="p-4 sm:p-6 overflow-y-auto space-y-4 flex-1">
              {loadingDetails ? (
                <div className="py-16 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="w-6 h-6 text-brand-500 animate-spin" />
                  <span>Loading document metadata and extracted text...</span>
                </div>
              ) : detailsError ? (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                  {detailsError}
                </div>
              ) : fileDetails ? (
                <>
                  {/* Metadata Chips */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block font-semibold">Format</span>
                      <span className="text-xs font-semibold text-slate-200 mt-0.5 block">
                        {fileDetails.extension} ({fileDetails.mime_type})
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block font-semibold">Size</span>
                      <span className="text-xs font-semibold text-slate-200 mt-0.5 block">
                        {formatBytes(fileDetails.size)}
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block font-semibold">Chunks Indexed</span>
                      <span className="text-xs font-semibold text-brand-400 mt-0.5 block">
                        {fileDetails.text_chunk_count} chunks
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block font-semibold">Processing</span>
                      <span className="text-xs font-semibold text-emerald-400 mt-0.5 uppercase block">
                        {fileDetails.processing_status}
                      </span>
                    </div>
                  </div>

                  {fileDetails.error_message && (
                    <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                      <span className="font-semibold block mb-0.5">Error Notice:</span>
                      {fileDetails.error_message}
                    </div>
                  )}

                  {/* Extracted Text Section */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                        Extracted Text (OCR / Parsed)
                      </h4>
                      <span className="text-[11px] text-slate-500">
                        {fileDetails.extracted_text ? `${fileDetails.extracted_text.length} characters` : 'No text'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 font-mono text-xs text-slate-300 whitespace-pre-wrap max-h-72 overflow-y-auto leading-relaxed selection:bg-brand-500/40">
                      {fileDetails.extracted_text || (
                        <span className="text-slate-600 italic">No text content was extracted for this file.</span>
                      )}
                    </div>
                  </div>

                  {/* Security Notice */}
                  <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800 text-[11px] text-slate-500">
                    <span className="font-semibold text-slate-400 block mb-0.5">Security Notice:</span>
                    Original physical server paths are protected by backend isolation. Only user-sanitized metadata and parsed text are returned.
                  </div>
                </>
              ) : null}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-slate-800 flex justify-end">
              <button
                onClick={closeDetails}
                className="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
