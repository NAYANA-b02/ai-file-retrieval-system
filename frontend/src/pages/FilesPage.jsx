import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { useToast } from '../context/ToastContext';
import { 
  FolderOpen, 
  Search, 
  UploadCloud, 
  RefreshCw, 
  FileText, 
  FileImage, 
  ExternalLink, 
  Eye, 
  Download, 
  Trash2, 
  Loader2, 
  AlertCircle,
  Calendar,
  HardDrive,
  Layers,
  CheckCircle2,
  Clock,
  XCircle
} from 'lucide-react';
import FilePreviewModal from '../components/FilePreviewModal';
import DeleteModal from '../components/DeleteModal';

export default function FilesPage() {
  const { showSuccess, showError } = useToast();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Modals state
  const [previewFile, setPreviewFile] = useState(null);
  const [deleteTargetFile, setDeleteTargetFile] = useState(null);
  const [deleting, setDeleting] = useState(false);

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

  // 1. OPEN ACTION
  const handleOpen = async (file) => {
    try {
      const res = await api.get(`/files/${file.id}/content`, { responseType: 'blob' });
      const blobUrl = URL.createObjectURL(res.data);
      window.open(blobUrl, '_blank');
    } catch (err) {
      showError(err.message || 'Unable to open file.');
    }
  };

  // 2. VIEW ACTION
  const handleView = (file) => {
    setPreviewFile(file);
  };

  // 3. DOWNLOAD ACTION
  const handleDownload = async (file) => {
    try {
      const res = await api.get(`/files/${file.id}/content?download=true`, { responseType: 'blob' });
      const blobUrl = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = file.original_filename || 'downloaded_file';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
      showSuccess(`Downloading "${file.original_filename}"...`);
    } catch (err) {
      showError(err.message || 'Download failed.');
    }
  };

  // 4. DELETE ACTION
  const handleDeletePrompt = (file) => {
    setDeleteTargetFile(file);
  };

  const confirmDelete = async () => {
    if (!deleteTargetFile) return;
    setDeleting(true);
    try {
      await api.delete(`/files/${deleteTargetFile.id}`);
      showSuccess(`"${deleteTargetFile.original_filename}" was permanently deleted.`);
      setFiles((prev) => prev.filter((f) => f.id !== deleteTargetFile.id));
      setDeleteTargetFile(null);
    } catch (err) {
      showError(err.message || 'Failed to delete file.');
    } finally {
      setDeleting(false);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getFileIcon = (ext) => {
    const cleanExt = (ext || '').toLowerCase();
    if (['.png', '.jpg', '.jpeg'].includes(cleanExt)) {
      return <FileImage className="w-5 h-5 text-[#3B82F6]" />;
    }
    return <FileText className="w-5 h-5 text-[#7C3AED]" />;
  };

  const filteredFiles = files.filter((f) =>
    f.original_filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-7">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight">
            My Files
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Manage your uploaded documents, view extracted OCR text, and control vault storage.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={fetchFiles}
            disabled={loading}
            className="p-2.5 rounded-2xl bg-white border border-[#E2E8F0] text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition shadow-subtle text-xs flex items-center gap-1.5"
            title="Refresh list"
            aria-label="Refresh files"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-[#A78BFA]' : ''}`} />
            <span className="hidden sm:inline font-semibold">Refresh</span>
          </button>

          <Link
            to="/upload"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-[#A78BFA] hover:bg-[#8B5CF6] text-white text-xs font-bold shadow-subtle hover:shadow-card transition"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload File</span>
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-[#E2E8F0] rounded-3xl p-3 sm:p-4 shadow-subtle">
        <div className="relative max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search documents by name..."
            className="w-full pl-10 pr-4 py-2.5 bg-[#F8F7FC] border border-[#E2E8F0] rounded-2xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#A78BFA] focus:ring-2 focus:ring-[#A78BFA]/20 transition"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-[#FFF1F2] border border-[#FDA4AF] text-[#9F1239] text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-[#E11D48]" />
          <span>{error}</span>
        </div>
      )}

      {/* Files List Container */}
      <div className="bg-white border border-[#E2E8F0] rounded-3xl overflow-hidden shadow-subtle">
        {loading ? (
          <div className="py-20 text-center flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-7 h-7 text-[#A78BFA] animate-spin" />
            <p className="text-xs font-semibold text-slate-500">Loading documents...</p>
          </div>
        ) : filteredFiles.length === 0 ? (
          <div className="py-16 text-center space-y-3 px-4">
            <div className="w-12 h-12 rounded-2xl bg-[#F8F7FC] text-slate-400 flex items-center justify-center mx-auto">
              <FolderOpen className="w-6 h-6" />
            </div>
            <p className="text-sm font-bold text-slate-700">
              {searchTerm ? 'No matching documents' : 'No documents yet'}
            </p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {searchTerm
                ? 'Try different keywords or clear your search filter.'
                : 'Upload your first document to start searching and asking questions.'}
            </p>
            {!searchTerm && (
              <Link
                to="/upload"
                className="inline-block mt-2 px-4 py-2 rounded-xl bg-[#EDE9FE] text-[#7C3AED] text-xs font-bold hover:bg-[#DDD6FE] transition"
              >
                Upload Document
              </Link>
            )}
          </div>
        ) : (
          <>
            {/* Desktop Table Layout */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-[#FAF8FF] border-b border-[#E2E8F0] text-slate-500 font-bold uppercase tracking-wider text-[11px]">
                    <th className="py-4 px-5">Document</th>
                    <th className="py-4 px-4">Format</th>
                    <th className="py-4 px-4">Size</th>
                    <th className="py-4 px-4">Status</th>
                    <th className="py-4 px-4">Chunks</th>
                    <th className="py-4 px-4">Uploaded</th>
                    <th className="py-4 px-5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F1F5F9]">
                  {filteredFiles.map((file) => (
                    <tr key={file.id} className="hover:bg-[#F8F7FC] transition group">
                      {/* Document Name */}
                      <td className="py-3.5 px-5">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-[#FAF8FF] border border-[#E2E8F0] flex items-center justify-center shrink-0">
                            {getFileIcon(file.extension)}
                          </div>
                          <span className="font-semibold text-slate-800 truncate max-w-xs block">
                            {file.original_filename}
                          </span>
                        </div>
                      </td>

                      {/* Format */}
                      <td className="py-3.5 px-4">
                        <span className="uppercase font-mono text-[10px] font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                          {(file.extension || '').replace('.', '')}
                        </span>
                      </td>

                      {/* Size */}
                      <td className="py-3.5 px-4 text-slate-600 font-medium">
                        {formatBytes(file.size)}
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                            file.processing_status === 'completed'
                              ? 'bg-[#F0FDF4] text-[#166534] border border-[#BBF7D0]'
                              : file.processing_status === 'failed'
                              ? 'bg-[#FFF1F2] text-[#9F1239] border border-[#FDA4AF]'
                              : 'bg-[#FFF7ED] text-[#9A3412] border border-[#FED7AA]'
                          }`}
                        >
                          {file.processing_status === 'completed' && <CheckCircle2 className="w-3 h-3 text-[#16A34A]" />}
                          {file.processing_status === 'failed' && <XCircle className="w-3 h-3 text-[#E11D48]" />}
                          {(file.processing_status === 'processing' || file.processing_status === 'uploaded') && (
                            <Clock className="w-3 h-3 text-[#EA580C]" />
                          )}
                          <span>{file.processing_status === 'completed' ? 'Processed' : file.processing_status === 'failed' ? 'Failed' : 'Processing'}</span>
                        </span>
                      </td>

                      {/* Chunks */}
                      <td className="py-3.5 px-4 text-slate-600 font-medium">
                        <span className="inline-flex items-center gap-1 text-slate-500">
                          <Layers className="w-3.5 h-3.5 text-[#A78BFA]" />
                          <span>{file.text_chunk_count || 0}</span>
                        </span>
                      </td>

                      {/* Upload Date */}
                      <td className="py-3.5 px-4 text-slate-500">
                        {new Date(file.uploaded_at).toLocaleDateString()}
                      </td>

                      {/* Four Functional Actions: OPEN, VIEW, DOWNLOAD, DELETE */}
                      <td className="py-3.5 px-5 text-right">
                        <div className="inline-flex items-center gap-1">
                          {/* OPEN */}
                          <button
                            onClick={() => handleOpen(file)}
                            className="p-1.5 rounded-xl text-slate-500 hover:text-[#7C3AED] hover:bg-[#EDE9FE] transition"
                            title="Open in new tab"
                            aria-label={`Open ${file.original_filename} in new tab`}
                          >
                            <ExternalLink className="w-4 h-4" />
                          </button>

                          {/* VIEW */}
                          <button
                            onClick={() => handleView(file)}
                            className="p-1.5 rounded-xl text-slate-500 hover:text-[#7C3AED] hover:bg-[#EDE9FE] transition"
                            title="View document preview"
                            aria-label={`Preview ${file.original_filename}`}
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {/* DOWNLOAD */}
                          <button
                            onClick={() => handleDownload(file)}
                            className="p-1.5 rounded-xl text-slate-500 hover:text-[#7C3AED] hover:bg-[#EDE9FE] transition"
                            title="Download original file"
                            aria-label={`Download ${file.original_filename}`}
                          >
                            <Download className="w-4 h-4" />
                          </button>

                          {/* DELETE */}
                          <button
                            onClick={() => handleDeletePrompt(file)}
                            className="p-1.5 rounded-xl text-slate-400 hover:text-[#E11D48] hover:bg-[#FFF1F2] transition"
                            title="Delete file"
                            aria-label={`Delete ${file.original_filename}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards Layout */}
            <div className="md:hidden divide-y divide-[#F1F5F9] p-2">
              {filteredFiles.map((file) => (
                <div key={file.id} className="p-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 rounded-2xl bg-[#FAF8FF] border border-[#E2E8F0] flex items-center justify-center shrink-0">
                        {getFileIcon(file.extension)}
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-slate-800 text-xs truncate">
                          {file.original_filename}
                        </p>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {formatBytes(file.size)} • {(file.extension || '').toUpperCase()}
                        </p>
                      </div>
                    </div>

                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold shrink-0 ${
                        file.processing_status === 'completed'
                          ? 'bg-[#F0FDF4] text-[#166534] border border-[#BBF7D0]'
                          : file.processing_status === 'failed'
                          ? 'bg-[#FFF1F2] text-[#9F1239] border border-[#FDA4AF]'
                          : 'bg-[#FFF7ED] text-[#9A3412] border border-[#FED7AA]'
                      }`}
                    >
                      {file.processing_status === 'completed' ? 'Processed' : file.processing_status === 'failed' ? 'Failed' : 'Processing'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                    <span>Uploaded {new Date(file.uploaded_at).toLocaleDateString()}</span>
                    <span>{file.text_chunk_count || 0} chunks</span>
                  </div>

                  {/* Actions Bar for Mobile */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                    <button
                      onClick={() => handleView(file)}
                      className="inline-flex items-center gap-1 text-xs font-bold text-[#7C3AED] px-2 py-1 rounded-lg hover:bg-[#EDE9FE]"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>View</span>
                    </button>

                    <button
                      onClick={() => handleOpen(file)}
                      className="inline-flex items-center gap-1 text-xs font-bold text-slate-600 px-2 py-1 rounded-lg hover:bg-slate-100"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>Open</span>
                    </button>

                    <button
                      onClick={() => handleDownload(file)}
                      className="inline-flex items-center gap-1 text-xs font-bold text-slate-600 px-2 py-1 rounded-lg hover:bg-slate-100"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download</span>
                    </button>

                    <button
                      onClick={() => handleDeletePrompt(file)}
                      className="inline-flex items-center gap-1 text-xs font-bold text-[#E11D48] px-2 py-1 rounded-lg hover:bg-[#FFF1F2]"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Delete</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* In-App Document Preview Modal */}
      {previewFile && (
        <FilePreviewModal
          file={previewFile}
          isOpen={Boolean(previewFile)}
          onClose={() => setPreviewFile(null)}
          onDownload={handleDownload}
          onOpenTab={handleOpen}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteTargetFile && (
        <DeleteModal
          isOpen={Boolean(deleteTargetFile)}
          filename={deleteTargetFile.original_filename}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTargetFile(null)}
          deleting={deleting}
        />
      )}
    </div>
  );
}
