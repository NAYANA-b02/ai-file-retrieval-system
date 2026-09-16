import React, { useEffect } from 'react';
import { AlertTriangle, Trash2, X, Loader2 } from 'lucide-react';

export default function DeleteModal({ isOpen, filename, onConfirm, onCancel, deleting }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen && !deleting) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, deleting, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-modal-title"
    >
      <div 
        className="bg-white border border-[#E2E8F0] rounded-3xl p-6 sm:p-7 max-w-md w-full shadow-card animate-fade-in space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-[#FFF1F2] border border-[#FDA4AF] flex items-center justify-center shrink-0">
            <AlertTriangle className="w-6 h-6 text-[#E11D48]" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 id="delete-modal-title" className="text-base font-bold text-slate-800">
              Delete document?
            </h3>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Are you sure you want to permanently delete{' '}
              <span className="font-semibold text-slate-800 break-all">{filename}</span>?
            </p>
            <p className="text-xs text-rose-600 font-medium mt-1">
              This action cannot be undone.
            </p>
          </div>
          <button
            onClick={onCancel}
            disabled={deleting}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onCancel}
            disabled={deleting}
            className="px-4 py-2.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={deleting}
            className="px-5 py-2.5 rounded-xl bg-[#FDA4AF] hover:bg-[#FB7185] text-slate-900 text-xs font-bold transition shadow-sm flex items-center gap-1.5 disabled:opacity-50"
          >
            {deleting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
