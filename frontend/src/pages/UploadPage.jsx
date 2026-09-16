import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { useToast } from '../context/ToastContext';
import { 
  UploadCloud, 
  FileText, 
  FileImage, 
  CheckCircle2, 
  AlertCircle, 
  X, 
  Loader2, 
  Search, 
  Bot, 
  FolderOpen,
  Sparkles,
  ShieldCheck
} from 'lucide-react';

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg'];
const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export default function UploadPage() {
  const { showSuccess, showError } = useToast();
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
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

    if (file.size > MAX_SIZE_BYTES) {
      setError(`File exceeds the maximum limit of ${MAX_SIZE_MB} MB.`);
      return;
    }

    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`Unsupported file extension (${ext}). Supported: PDF, DOCX, TXT, PNG, JPG.`);
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
    setProcessingStage('Uploading document to secure storage...');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setProcessingStage('Extracting text & running OCR...');

      const res = await api.post('/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResult(res.data);
      showSuccess(`"${selectedFile.name}" uploaded successfully!`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setError(err.message || 'File upload failed.');
      showError(err.message || 'File upload failed.');
    } finally {
      setUploading(false);
      setProcessingStage('');
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const clearSelectedFile = () => {
    setSelectedFile(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="max-w-3xl mx-auto space-y-7">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight">
          Upload Documents
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Upload PDF, Word (DOCX), Text, or Scanned Images for automatic text extraction, OCR, chunking, and embedding.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-[#FFF1F2] border border-[#FDA4AF] text-[#9F1239] text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-[#E11D48]" />
          <span>{error}</span>
        </div>
      )}

      {/* Success Banner */}
      {result && (
        <div className="p-6 rounded-3xl bg-[#F0FDF4] border border-[#BBF7D0] shadow-subtle space-y-4 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#BBF7D0] text-[#166534] flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-800">Upload Successful</h2>
              <p className="text-xs text-slate-600">
                <span className="font-semibold">{result.original_filename}</span> ({formatBytes(result.size)}) has been saved to your vault.
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-2xl bg-white/80 border border-[#BBF7D0] text-xs text-slate-600 flex items-center justify-between">
            <span className="font-medium">Current Status:</span>
            <span className="font-bold px-2.5 py-0.5 rounded-full bg-[#BBF7D0] text-[#166534] uppercase text-[10px]">
              {result.processing_status}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Link
              to="/files"
              className="px-4 py-2 rounded-xl bg-white border border-[#BBF7D0] text-[#166534] hover:bg-[#BBF7D0]/30 text-xs font-bold transition flex items-center gap-1.5"
            >
              <FolderOpen className="w-3.5 h-3.5" />
              <span>View in My Files</span>
            </Link>

            <Link
              to="/search"
              className="px-4 py-2 rounded-xl bg-[#A78BFA] hover:bg-[#8B5CF6] text-white text-xs font-bold transition flex items-center gap-1.5"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search Document</span>
            </Link>

            <Link
              to="/rag"
              className="px-4 py-2 rounded-xl bg-white border border-[#E2E8F0] text-slate-700 hover:bg-slate-50 text-xs font-bold transition flex items-center gap-1.5"
            >
              <Bot className="w-3.5 h-3.5" />
              <span>Ask AI</span>
            </Link>
          </div>
        </div>
      )}

      {/* Drag & Drop Area */}
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        className={`bg-white border-2 border-dashed rounded-3xl p-8 sm:p-12 text-center transition-all duration-200 shadow-subtle ${
          dragActive
            ? 'border-[#A78BFA] bg-[#FAF8FF] scale-[1.01]'
            : 'border-[#E2E8F0] hover:border-[#CBD5E1]'
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

        <div className="w-16 h-16 rounded-3xl bg-[#EDE9FE] text-[#7C3AED] flex items-center justify-center mx-auto mb-4 shadow-subtle">
          <UploadCloud className="w-8 h-8" />
        </div>

        <h2 className="text-base font-bold text-slate-800">
          Drag &amp; drop your files here
        </h2>
        <p className="text-xs text-slate-500 mt-1">or</p>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="mt-3 px-5 py-2.5 rounded-2xl bg-[#EDE9FE] hover:bg-[#DDD6FE] text-[#7C3AED] text-xs font-bold transition shadow-subtle"
        >
          Browse Files
        </button>

        {/* Format Badges */}
        <div className="mt-8 pt-6 border-t border-slate-100 flex flex-wrap items-center justify-center gap-2 text-[11px] text-slate-500">
          <span className="font-semibold text-slate-600 mr-1">Supported:</span>
          <span className="px-2.5 py-1 rounded-lg bg-[#EFF6FF] text-[#1E40AF] font-mono font-semibold">PDF</span>
          <span className="px-2.5 py-1 rounded-lg bg-[#EFF6FF] text-[#1E40AF] font-mono font-semibold">DOCX</span>
          <span className="px-2.5 py-1 rounded-lg bg-[#F0FDF4] text-[#166534] font-mono font-semibold">TXT</span>
          <span className="px-2.5 py-1 rounded-lg bg-[#FAF8FF] text-[#7C3AED] font-mono font-semibold">PNG</span>
          <span className="px-2.5 py-1 rounded-lg bg-[#FAF8FF] text-[#7C3AED] font-mono font-semibold">JPG</span>
          <span className="text-slate-300 mx-1">•</span>
          <span className="font-semibold text-slate-600">Maximum size:</span>
          <span className="px-2.5 py-1 rounded-lg bg-[#FFF7ED] text-[#9A3412] font-semibold">10 MB</span>
        </div>
      </div>

      {/* Selected File Card */}
      {selectedFile && (
        <div className="bg-white border border-[#E2E8F0] rounded-3xl p-5 shadow-subtle space-y-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-2xl bg-[#FAF8FF] border border-[#E2E8F0] flex items-center justify-center text-[#7C3AED] shrink-0">
                {selectedFile.type.startsWith('image/') ? (
                  <FileImage className="w-5 h-5 text-[#3B82F6]" />
                ) : (
                  <FileText className="w-5 h-5 text-[#7C3AED]" />
                )}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-800 truncate">{selectedFile.name}</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {formatBytes(selectedFile.size)} • {selectedFile.type || 'Document'}
                </p>
              </div>
            </div>

            {!uploading && (
              <button
                onClick={clearSelectedFile}
                className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
                aria-label="Remove selected file"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Processing Indicator */}
          {uploading && (
            <div className="p-3.5 rounded-2xl bg-[#FAF8FF] border border-[#EDE9FE] flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-[#A78BFA] animate-spin shrink-0" />
              <p className="text-xs font-semibold text-[#7C3AED]">{processingStage}</p>
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full py-3 px-4 bg-[#A78BFA] hover:bg-[#8B5CF6] text-white rounded-2xl text-xs sm:text-sm font-bold shadow-subtle hover:shadow-card transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing Document...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-4 h-4" />
                <span>Start Upload &amp; OCR</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Security note */}
      <div className="p-4 rounded-3xl bg-white border border-[#E2E8F0] text-xs text-slate-500 flex items-start gap-3 shadow-subtle">
        <ShieldCheck className="w-4 h-4 text-[#16A34A] shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <span className="font-bold text-slate-700">Storage Protection:</span> Files are stored under unique UUID references in your private user space. Physical filesystem directories are never exposed.
        </p>
      </div>
    </div>
  );
}
