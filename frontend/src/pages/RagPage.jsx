import React, { useState, useEffect, useMemo } from 'react';
import api from '../api/client';
import { useToast } from '../context/ToastContext';
import { 
  Bot, 
  Send, 
  Sparkles, 
  FileText, 
  AlertCircle, 
  Loader2, 
  CheckCircle2, 
  Quote, 
  Layers,
  HelpCircle,
  ExternalLink,
  Eye,
  Award,
  Filter,
  Image as ImageIcon
} from 'lucide-react';
import FilePreviewModal from '../components/FilePreviewModal';

export default function RagPage() {
  const { showError } = useToast();
  const [question, setQuestion] = useState('');
  const [topK, setTopK] = useState(5);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Document filter state
  const [userFiles, setUserFiles] = useState([]);
  const [selectedFileId, setSelectedFileId] = useState(null);

  // File Preview Modal for citation sources
  const [previewFile, setPreviewFile] = useState(null);

  // Fetch user's files for the document filter dropdown
  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const res = await api.get('/files');
        setUserFiles(res.data || []);
      } catch {
        // Non-blocking: dropdown shows "All Documents" only
      }
    };
    fetchFiles();
  }, []);

  const sampleQuestions = [
    'What are the key findings or topics covered across my documents?',
    'Summarize the primary responsibilities and qualifications mentioned.',
    'What dates and deadlines are referenced in the uploaded files?',
  ];

  const handleAsk = async (e) => {
    e?.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const payload = {
        question: question.trim(),
        top_k: Number(topK),
      };

      // Add file_id filter if a specific document is selected
      if (selectedFileId) {
        payload.file_id = Number(selectedFileId);
      }

      const res = await api.post('/rag/ask', payload);
      setResponse(res.data);
    } catch (err) {
      setError(err.message || 'RAG generation failed.');
      showError(err.message || 'RAG generation failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleViewSource = async (fileId, filename) => {
    try {
      const res = await api.get(`/files/${fileId}`);
      setPreviewFile(res.data);
    } catch {
      setPreviewFile({ id: fileId, original_filename: filename || 'Document' });
    }
  };

  // Derive selected file name for display
  const selectedFileName = useMemo(() => {
    if (!selectedFileId) return null;
    const file = userFiles.find(f => f.id === Number(selectedFileId));
    return file?.original_filename || `Document #${selectedFileId}`;
  }, [selectedFileId, userFiles]);

  // Build the visual image URL (uses session cookie auth via withCredentials)
  const getVisualUrl = (visual) => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
    return `${baseUrl}/files/${visual.file_id}/visuals/${visual.visual_id}`;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-7">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#EDE9FE] text-[#7C3AED] text-xs font-bold mb-2 shadow-subtle">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Grounded RAG Assistant</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight">
          Ask Your Documents
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Ask questions and get answers grounded in your uploaded files.
        </p>
      </div>

      {/* Question Form Card */}
      <div className="bg-white border border-[#E2E8F0] rounded-3xl p-5 sm:p-6 shadow-subtle space-y-4">
        <form onSubmit={handleAsk} className="space-y-3">
          <div className="relative">
            <textarea
              rows={3}
              required
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your uploaded documents (e.g. 'What is the summary of project deliverables?')..."
              className="w-full p-4 bg-[#F8F7FC] border border-transparent rounded-2xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-[#A78BFA] focus:ring-2 focus:ring-[#A78BFA]/20 transition resize-none leading-relaxed"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            {/* Document Filter Dropdown */}
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Filter className="w-3.5 h-3.5 text-[#7C3AED]" />
              <span className="font-semibold text-slate-600">Scope:</span>
              <select
                value={selectedFileId || ''}
                onChange={(e) => setSelectedFileId(e.target.value || null)}
                className="bg-[#F8F7FC] border border-[#E2E8F0] text-slate-700 text-xs rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-[#A78BFA] max-w-[220px] truncate"
              >
                <option value="">All Documents</option>
                {userFiles.map((file) => (
                  <option key={file.id} value={file.id}>
                    {file.original_filename}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="font-semibold">Context Chunks (top_k):</span>
                <select
                  value={topK}
                  onChange={(e) => setTopK(e.target.value)}
                  className="bg-[#F8F7FC] border border-[#E2E8F0] text-slate-700 text-xs rounded-xl px-2.5 py-1 focus:outline-none focus:border-[#A78BFA]"
                >
                  <option value={3}>3 chunks</option>
                  <option value={5}>5 chunks (Standard)</option>
                  <option value={8}>8 chunks</option>
                  <option value={10}>10 chunks</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={loading || !question.trim()}
                className="py-2.5 px-5 bg-[#A78BFA] hover:bg-[#8B5CF6] text-white rounded-2xl text-xs font-bold shadow-subtle hover:shadow-card transition flex items-center gap-2 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Generate Grounded Answer</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Sample Prompts */}
        {!response && !loading && (
          <div className="pt-4 border-t border-slate-100">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
              Try an example question:
            </span>
            <div className="flex flex-wrap gap-2">
              {sampleQuestions.map((sq, i) => (
                <button
                  key={i}
                  onClick={() => setQuestion(sq)}
                  className="text-left text-xs text-slate-600 hover:text-[#7C3AED] bg-[#F8F7FC] hover:bg-[#FAF8FF] border border-[#E2E8F0] hover:border-[#A78BFA] px-3 py-1.5 rounded-xl transition font-medium"
                >
                  "{sq}"
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-[#FFF1F2] border border-[#FDA4AF] text-[#9F1239] text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-[#E11D48]" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State with Meaningful Stages */}
      {loading && (
        <div className="bg-white border border-[#E2E8F0] rounded-3xl p-8 shadow-subtle text-center space-y-4 animate-fade-in">
          <div className="w-12 h-12 rounded-2xl bg-[#EDE9FE] text-[#7C3AED] flex items-center justify-center mx-auto">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-800">
              Analyzing your documents...
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Retrieving relevant context and generating a strictly grounded answer.
              {selectedFileName && (
                <span className="text-[#7C3AED] font-semibold"> (Scoped to "{selectedFileName}")</span>
              )}
            </p>
          </div>

          <div className="max-w-md mx-auto grid grid-cols-3 gap-2 text-[10px] text-slate-500 pt-2">
            <div className="p-2 rounded-xl bg-[#FAF8FF] border border-[#E2E8F0]">
              <span className="font-semibold block text-slate-700">1. Search</span>
              <span>Finding documents</span>
            </div>
            <div className="p-2 rounded-xl bg-[#FAF8FF] border border-[#E2E8F0]">
              <span className="font-semibold block text-slate-700">2. Retrieve</span>
              <span>Relevant sections</span>
            </div>
            <div className="p-2 rounded-xl bg-[#FAF8FF] border border-[#E2E8F0]">
              <span className="font-semibold block text-slate-700">3. Generate</span>
              <span>Grounded answer</span>
            </div>
          </div>
        </div>
      )}

      {/* Answer Area */}
      {response && !loading && (
        <div className="space-y-5 animate-fade-in">

          {/* Document Visual Card (if the RAG found an original diagram/visual) */}
          {response.visuals && response.visuals.length > 0 && (
            <div className="bg-white border border-[#E2E8F0] rounded-3xl p-5 sm:p-6 shadow-subtle space-y-4">
              <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
                <div className="w-8 h-8 rounded-xl bg-[#FEF3C7] text-[#D97706] flex items-center justify-center">
                  <ImageIcon className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Original Document Visual
                  </h2>
                  <p className="text-[11px] text-slate-400">
                    Extracted directly from your uploaded document — not AI generated
                  </p>
                </div>
              </div>

              {response.visuals.map((visual, idx) => (
                <div key={idx} className="space-y-3">
                  {/* Visual image displayed securely via authenticated endpoint */}
                  <div className="rounded-2xl border border-[#E2E8F0] overflow-hidden bg-[#F8F7FC]">
                    <img
                      src={getVisualUrl(visual)}
                      alt={visual.caption || `Document visual from ${visual.original_filename}`}
                      className="w-full h-auto max-h-[500px] object-contain"
                      loading="lazy"
                      crossOrigin="use-credentials"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextSibling && (e.target.nextSibling.style.display = 'flex');
                      }}
                    />
                    <div className="hidden items-center justify-center p-8 text-slate-400 text-xs">
                      <AlertCircle className="w-4 h-4 mr-2" />
                      Unable to load visual
                    </div>
                  </div>

                  {/* Visual metadata */}
                  <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                    <span className="inline-flex items-center gap-1 bg-[#FEF3C7] text-[#92400E] px-2 py-0.5 rounded-lg font-bold">
                      <ImageIcon className="w-3 h-3" />
                      {visual.visual_type === 'page_render' ? 'Page Render' : visual.visual_type === 'embedded_image' ? 'Embedded Image' : 'Image'}
                    </span>
                    <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      {visual.original_filename}
                    </span>
                    {visual.page_number && (
                      <span>Page {visual.page_number}</span>
                    )}
                    {visual.caption && (
                      <span className="italic text-slate-400">"{visual.caption}"</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Answer Card */}
          <div className="bg-white border border-[#E2E8F0] rounded-3xl p-6 sm:p-7 shadow-subtle space-y-4">
            <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
              <div className="w-8 h-8 rounded-xl bg-[#F0FDF4] text-[#16A34A] flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Grounded Answer
                </h2>
                <p className="text-[11px] text-slate-400">
                  Synthesized from your document vault
                  {selectedFileName && (
                    <span className="text-[#7C3AED] font-semibold ml-1">• Scoped to "{selectedFileName}"</span>
                  )}
                </p>
              </div>
            </div>

            <div className="text-xs sm:text-sm text-slate-700 font-sans leading-relaxed whitespace-pre-wrap selection:bg-[#EDE9FE]">
              {response.answer || (
                <span className="text-slate-500 italic">
                  I couldn't find enough relevant information in your uploaded documents to answer this question.
                </span>
              )}
            </div>
          </div>

          {/* Sources Section Underneath */}
          {response.citations && response.citations.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-bold text-slate-600 uppercase tracking-wider px-1">
                Grounded Citations ({response.citations.length})
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {response.citations.map((c, idx) => (
                  <div
                    key={idx}
                    className="bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-subtle hover:shadow-card transition space-y-2.5 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="w-4 h-4 text-[#7C3AED] shrink-0" />
                          <span className="text-xs font-bold text-slate-800 truncate">
                            {c.filename || c.original_filename || `Document #${c.file_id}`}
                          </span>
                        </div>

                        {c.similarity_score !== undefined && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#EDE9FE] text-[#7C3AED] shrink-0">
                            {(c.similarity_score * 100).toFixed(1)}% match
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-slate-600 bg-[#F8F7FC] p-2.5 rounded-xl border border-slate-100 mt-2 line-clamp-3 leading-relaxed">
                        "{c.text || c.chunk_text || c.snippet || 'Source excerpt'}"
                      </p>
                    </div>

                    <div className="flex items-center justify-between pt-1 text-[11px] text-slate-400">
                      <span>Chunk #{c.chunk_index !== undefined ? c.chunk_index + 1 : idx + 1}</span>
                      {c.file_id && (
                        <button
                          onClick={() => handleViewSource(c.file_id, c.filename)}
                          className="inline-flex items-center gap-1 text-[#7C3AED] font-semibold hover:underline"
                        >
                          <Eye className="w-3 h-3" />
                          <span>View Doc</span>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

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
