import React, { useState, useRef } from 'react';
import api from '../api/client';
import { 
  UploadCloud, 
  FileCheck, 
  AlertCircle, 
  CheckCircle2, 
  Loader2, 
  FileType, 
  X, 
  Layers, 
  Eye 
} from 'lucide-react';
import { Link } from 'react-router-dom';

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg'];
const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export default function UploadPage() {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateAndSetFile = (file) => {
    setError(null);
    setResult(null);

    if (!file) return;

    // Check size
    if (file.size > MAX_SIZE_BYTES) {
      setError(`File exceeds the maximum allowed size of ${MAX_SIZE_MB}MB.`);
      return;
    }

    // Check extension
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`Unsupported file extension (${ext}). Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`);
      return;
    }

    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError(null);
    setResult(null);
    setUploadProgress(10);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Simulate progress progression for better UX
      const progressTimer = setInterval(() => {
        setUploadProgress((prev) => (prev < 80 ? prev + 15 : prev));
      }, 300);

      const res = await api.post('/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      clearInterval(progressTimer);
      setUploadProgress(100);
      setResult(res.data);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setError(err.message || 'File upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Upload Documents</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Upload PDF, Word (DOCX), Text, or Scanned Images for automatic text extraction, OCR, chunking, and embedding.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Success Banner */}
      {result && (
        <div className="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 space-y-3">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">Upload & Processing Complete!</h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs bg-slate-950/60 p-3.5 rounded-xl border border-emerald-500/20">
            <div>
              <span className="text-[11px] text-slate-400 block">Filename</span>
              <span className="font-semibold text-slate-200 truncate block">{result.original_filename}</span>
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block">Processing Status</span>
              <span className="font-semibold text-emerald-400 uppercase text-[11px]">{result.processing_status}</span>
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block">Vector Chunks</span>
              <span className="font-semibold text-slate-200 flex items-center gap-1">
                <Layers className="w-3 h-3 text-brand-400" />
                {result.text_chunk_count}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block">File Size</span>
              <span className="font-semibold text-slate-200">{formatBytes(result.size)}</span>
            </div>
          </div>
          <div className="flex items-center justify-end gap-3 pt-2">
            <Link
              to="/files"
              className="text-xs text-brand-300 hover:text-white font-medium flex items-center gap-1.5 transition"
            >
              <Eye className="w-3.5 h-3.5" />
              View in My Files &rarr;
            </Link>
          </div>
        </div>
      )}

      {/* Drag & Drop Card */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all ${
          dragActive
            ? 'border-brand-500 bg-brand-500/5'
            : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
          onChange={handleChange}
          className="hidden"
          id="file-upload-input"
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-brand-600/10 border border-brand-500/20 text-brand-400 flex items-center justify-center shadow-lg shadow-brand-500/10">
            <UploadCloud className="w-8 h-8" />
          </div>

          <div>
            <p className="text-sm font-semibold text-slate-200">
              Drag and drop your file here, or{' '}
              <label
                htmlFor="file-upload-input"
                className="text-brand-400 hover:text-brand-300 cursor-pointer underline underline-offset-2"
              >
                browse local files
              </label>
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports PDF, DOCX, TXT, PNG, JPG up to {MAX_SIZE_MB}MB
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
            {ALLOWED_EXTENSIONS.map((ext) => (
              <span
                key={ext}
                className="px-2 py-0.5 rounded-md bg-slate-800/80 border border-slate-700/60 text-[11px] font-mono text-slate-300 uppercase"
              >
                {ext.replace('.', '')}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Selected File Card & Actions */}
      {selectedFile && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center">
                <FileType className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200 truncate max-w-sm">
                  {selectedFile.name}
                </p>
                <p className="text-[11px] text-slate-500">{formatBytes(selectedFile.size)}</p>
              </div>
            </div>
            {!uploading && (
              <button
                onClick={() => {
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Progress bar */}
          {uploading && (
            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Extracting text & generating vector embeddings...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 transition-all duration-300 rounded-full"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="py-2.5 px-5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-brand-600/20 flex items-center gap-2 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing Document...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>Start Upload & Pipeline</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
