import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now() + Math.random().toString(36).substring(2, 7);
    setToasts((prev) => [...prev, { id, message, type }]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  }, [removeToast]);

  const showSuccess = useCallback((msg, duration) => addToast(msg, 'success', duration), [addToast]);
  const showError = useCallback((msg, duration) => addToast(msg, 'error', duration), [addToast]);
  const showInfo = useCallback((msg, duration) => addToast(msg, 'info', duration), [addToast]);

  return (
    <ToastContext.Provider value={{ showSuccess, showError, showInfo, addToast }}>
      {children}
      {/* Toast Notification Container */}
      <div 
        className="fixed top-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none px-3"
        role="region"
        aria-label="Notifications"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-2xl border shadow-card animate-fade-in transition-all duration-200 ${
              toast.type === 'success'
                ? 'bg-[#F0FDF4] border-[#BBF7D0] text-[#166534]'
                : toast.type === 'error'
                ? 'bg-[#FFF1F2] border-[#FDA4AF] text-[#9F1239]'
                : 'bg-[#EFF6FF] border-[#BFDBFE] text-[#1E40AF]'
            }`}
          >
            {toast.type === 'success' && <CheckCircle2 className="w-4 h-4 text-[#16A34A] shrink-0 mt-0.5" />}
            {toast.type === 'error' && <AlertCircle className="w-4 h-4 text-[#E11D48] shrink-0 mt-0.5" />}
            {toast.type === 'info' && <Info className="w-4 h-4 text-[#3B82F6] shrink-0 mt-0.5" />}

            <p className="text-xs font-medium leading-relaxed flex-1">{toast.message}</p>

            <button
              onClick={() => removeToast(toast.id)}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-black/5 transition -mr-1 -mt-1"
              aria-label="Close notification"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
