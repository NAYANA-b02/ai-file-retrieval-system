import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { 
  X, 
  FileText, 
  Download, 
  ExternalLink, 
  Loader2, 
  AlertCircle, 
  Layers, 
  Calendar, 
  HardDrive,
  Copy,
  Check
} from 'lucide-react';

export default function FilePreviewModal({ file, isOpen, onClose, onDownload, onOpenTab }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [blobUrl, setBlobUrl] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen || !file) {
      setDetails(null);
      setBlobUrl(null);
      setError(null);
      return;
    }

    let active = true;
    let currentBlobUrl = null;

    const loadData = async () => {
      setLoading(true);
      setError(null);

      try {
        // 1. Fetch metadata and extracted text
        const metaRes = await api.get(`/files/${file.id}`);
        if (!active) return;
        setDetails(metaRes.data);

        // 2. If it's an image or PDF, fetch blob for visual preview
        const ext = (file.extension || '').toLowerCase();
        if (['.pdf', '.png', '.jpg', '.jpeg'].includes(ext)) {
          const blobRes = await api.get(`/files/${file.id}/content`, {
            responseType: 'blob',
          });
          if (!active) return;
          currentBlobUrl = URL.createObjectURL(blobRes.data);
          setBlobUrl(currentBlobUrl);
        }
      } catch (err) {
        if (!active) return;
        setError(err.message || 'Unable to load document preview.');
      } finally {
        if (active) setLoading(false);
      }
    };

    loadData();

    return () => {
      active = false;
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
    };
  }, [isOpen, file]);

  const handleCopyText = () => {
    if (details?.extracted_text) {
      navigator.clipboard.writeText(details.extracted_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!isOpen || !file) return null;

  const ext = (file.extension || '').toLowerCase();
  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div
      className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="preview-modal-title"
    >
      <div 
        className="bg-white border border-[#E2E8F0] rounded-3xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-card animate-fade-in overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-[#E2E8F0] bg-[#FAF8FF] flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-2xl bg-[#EDE9FE] text-[#7C3AED] flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h2 id="preview-modal-title" className="text-sm sm:text-base font-bold text-slate-800 truncate">
                {file.original_filename}
              </h2>
              <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                <span className="uppercase font-semibold text-slate-600 bg-white px-2 py-0.5 rounded-md border border-[#E2E8F0]">
                  {ext.replace('.', '')}
                </span>
                <span>•</span>
                <span>{formatBytes(file.size)}</span>
                <span>•</span>
                <span>{file.text_chunk_count || 0} chunks</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {onOpenTab && (
              <button
                onClick={() => onOpenTab(file)}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#E2E8F0] bg-white text-xs font-semibold text-slate-700 hover:bg-[#F8F7FC] hover:text-[#7C3AED] transition"
                title="Open in new browser tab"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Open</span>
              </button>
            )}

            {onDownload && (
              <button
                onClick={() => onDownload(file)}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#E2E8F0] bg-white text-xs font-semibold text-slate-700 hover:bg-[#F8F7FC] hover:text-[#7C3AED] transition"
                title="Download original file"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download</span>
              </button>
            )}

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
              aria-label="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 overflow-y-auto flex-1 space-y-5">
          {loading ? (
            <div className="py-20 text-center flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-7 h-7 text-[#A78BFA] animate-spin" />
              <p className="text-xs font-medium text-slate-500">Loading document preview...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-2xl bg-[#FFF1F2] border border-[#FDA4AF] text-[#9F1239] text-xs flex items-center gap-3">
              <AlertCircle className="w-5 h-5 shrink-0 text-[#E11D48]" />
              <span>{error}</span>
            </div>
          ) : (
            <>
              {/* Image Preview */}
              {['.png', '.jpg', '.jpeg'].includes(ext) && blobUrl && (
                <div className="rounded-2xl border border-[#E2E8F0] bg-slate-50 p-4 flex items-center justify-center max-h-80 overflow-hidden">
                  <img
                    src={blobUrl}
                    alt={file.original_filename}
                    className="max-h-72 w-auto object-contain rounded-xl shadow-sm"
                  />
                </div>
              )}

              {/* PDF Preview Frame */}
              {ext === '.pdf' && blobUrl && (
                <div className="rounded-2xl border border-[#E2E8F0] overflow-hidden bg-slate-100 h-80 sm:h-96">
                  <iframe
                    src={blobUrl}
                    title={file.original_filename}
                    className="w-full h-full border-0"
                  />
                </div>
              )}

              {/* Extracted Text View (For TXT, DOCX, OCR, or general inspection) */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    {ext === '.docx' 
                      ? 'Extracted Document Content (DOCX)' 
                      : ext === '.txt' 
                      ? 'Document Text (TXT)' 
                      : 'Extracted / OCR Text'}
                  </h3>
                  {details?.extracted_text && (
                    <button
                      onClick={handleCopyText}
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#7C3AED] hover:underline"
                    >
                      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? 'Copied' : 'Copy Text'}</span>
                    </button>
                  )}
                </div>

                <div className="p-4 rounded-2xl bg-[#F8F7FC] border border-[#E2E8F0] text-xs text-slate-700 font-sans whitespace-pre-wrap max-h-64 sm:max-h-80 overflow-y-auto leading-relaxed selection:bg-[#EDE9FE]">
                  {details?.extracted_text ? (
                    details.extracted_text
                  ) : (
                    <span className="text-slate-400 italic">No text was extracted for this document.</span>
                  )}
                </div>
              </div>

              {/* Metadata Info Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                <div className="p-3 rounded-2xl bg-[#FAF8FF] border border-[#E2E8F0]">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Status</span>
                  <span className="text-xs font-bold text-[#16A34A] mt-0.5 capitalize block">
                    {details?.processing_status || file.processing_status}
                  </span>
                </div>
                <div className="p-3 rounded-2xl bg-[#FAF8FF] border border-[#E2E8F0]">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">MIME Type</span>
                  <span className="text-xs font-bold text-slate-700 mt-0.5 truncate block">
                    {file.mime_type}
                  </span>
                </div>
                <div className="p-3 rounded-2xl bg-[#FAF8FF] border border-[#E2E8F0]">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Indexed Chunks</span>
                  <span className="text-xs font-bold text-[#7C3AED] mt-0.5 block">
                    {details?.text_chunk_count ?? file.text_chunk_count}
                  </span>
                </div>
                <div className="p-3 rounded-2xl bg-[#FAF8FF] border border-[#E2E8F0]">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Uploaded</span>
                  <span className="text-xs font-bold text-slate-700 mt-0.5 block">
                    {new Date(file.uploaded_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#E2E8F0] bg-slate-50 flex items-center justify-between sm:justify-end gap-3">
          <div className="flex sm:hidden items-center gap-2">
            {onOpenTab && (
              <button
                onClick={() => onOpenTab(file)}
                className="px-3 py-2 rounded-xl border border-[#E2E8F0] bg-white text-xs font-semibold text-slate-700"
              >
                Open Tab
              </button>
            )}
            {onDownload && (
              <button
                onClick={() => onDownload(file)}
                className="px-3 py-2 rounded-xl border border-[#E2E8F0] bg-white text-xs font-semibold text-slate-700"
              >
                Download
              </button>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl bg-white border border-[#E2E8F0] text-slate-700 hover:bg-slate-100 text-xs font-bold transition shadow-subtle"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
