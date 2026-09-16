import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { useToast } from '../context/ToastContext';
import { 
  Search, 
  Sparkles, 
  Key, 
  SlidersHorizontal, 
  FileText, 
  ExternalLink, 
  Eye, 
  Loader2, 
  AlertCircle, 
  Layers, 
  Award,
  Hash
} from 'lucide-react';
import FilePreviewModal from '../components/FilePreviewModal';

export default function SearchPage() {
  const { showError, showSuccess } = useToast();
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';

  const [query, setQuery] = useState(initialQuery);
  const [searchMode, setSearchMode] = useState('hybrid'); // 'hybrid', 'semantic', 'keyword'
  const [topK, setTopK] = useState(5);
  const [semanticWeight, setSemanticWeight] = useState(0.6);
  const [keywordWeight, setKeywordWeight] = useState(0.4);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // File Preview Modal
  const [previewFile, setPreviewFile] = useState(null);

  const executeSearch = async (searchQuery, mode = searchMode) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);

    try {
      let endpoint = '/search/hybrid';
      let payload = {
        query: searchQuery.trim(),
        top_k: Number(topK),
      };

      if (mode === 'semantic') {
        endpoint = '/search/semantic';
      } else if (mode === 'keyword') {
        endpoint = '/search/keyword';
      } else {
        payload.semantic_weight = Number(semanticWeight);
        payload.keyword_weight = Number(keywordWeight);
      }

      const res = await api.post(endpoint, payload);
      setResults(res.data);
    } catch (err) {
      setError(err.message || 'Search request failed.');
      showError(err.message || 'Search failed.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialQuery) {
      executeSearch(initialQuery, 'hybrid');
    }
  }, [initialQuery]);

  const handleSearch = (e) => {
    e?.preventDefault();
    executeSearch(query);
  };

  const handleOpen = async (fileId) => {
    try {
      const res = await api.get(`/files/${fileId}/content`, { responseType: 'blob' });
      const blobUrl = URL.createObjectURL(res.data);
      window.open(blobUrl, '_blank');
    } catch (err) {
      showError(err.message || 'Unable to open document.');
    }
  };

  const handleView = async (fileId, filename) => {
    try {
      const res = await api.get(`/files/${fileId}`);
      setPreviewFile(res.data);
    } catch {
      setPreviewFile({ id: fileId, original_filename: filename || 'Document' });
    }
  };

  const handleSemanticWeightChange = (val) => {
    const sw = parseFloat(val);
    setSemanticWeight(sw);
    setKeywordWeight(parseFloat((1.0 - sw).toFixed(2)));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-7">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight">
          Search Documents
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Perform multi-modal search combining dense vector embeddings and sparse full-text keyword retrieval.
        </p>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 bg-white border border-[#E2E8F0] rounded-2xl w-fit shadow-subtle">
        <button
          type="button"
          onClick={() => {
            setSearchMode('hybrid');
            if (results) executeSearch(query, 'hybrid');
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition ${
            searchMode === 'hybrid'
              ? 'bg-[#EDE9FE] text-[#7C3AED] shadow-subtle'
              : 'text-slate-500 hover:text-slate-800 hover:bg-[#F8F7FC]'
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Hybrid Search</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setSearchMode('semantic');
            if (results) executeSearch(query, 'semantic');
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition ${
            searchMode === 'semantic'
              ? 'bg-[#EDE9FE] text-[#7C3AED] shadow-subtle'
              : 'text-slate-500 hover:text-slate-800 hover:bg-[#F8F7FC]'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Semantic</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setSearchMode('keyword');
            if (results) executeSearch(query, 'keyword');
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition ${
            searchMode === 'keyword'
              ? 'bg-[#EDE9FE] text-[#7C3AED] shadow-subtle'
              : 'text-slate-500 hover:text-slate-800 hover:bg-[#F8F7FC]'
          }`}
        >
          <Key className="w-3.5 h-3.5" />
          <span>Keyword</span>
        </button>
      </div>

      {/* Large Search Input Card */}
      <div className="bg-white border border-[#E2E8F0] rounded-3xl p-5 sm:p-6 shadow-subtle space-y-4">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <Search className="w-5 h-5 text-[#A78BFA]" />
            </div>
            <input
              type="text"
              required
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                searchMode === 'semantic'
                  ? 'Ask or describe concepts in plain English (e.g. "financial growth quarterly")...'
                  : searchMode === 'keyword'
                  ? 'Search exact keywords or phrases (e.g. "invoice total 2024")...'
                  : 'Enter query to combine semantic understanding and exact keyword matches...'
              }
              className="w-full pl-12 pr-28 py-3.5 bg-[#F8F7FC] border border-transparent rounded-2xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-[#A78BFA] focus:ring-2 focus:ring-[#A78BFA]/20 transition"
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-2 top-2 bottom-2 px-5 bg-[#A78BFA] hover:bg-[#8B5CF6] text-white rounded-xl text-xs font-bold shadow-subtle transition flex items-center gap-1.5 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Searching...</span>
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  <span>Search</span>
                </>
              )}
            </button>
          </div>

          {/* Configuration drawer for Hybrid parameters */}
          {searchMode === 'hybrid' && (
            <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-slate-600">Balance:</span>
                <span className="text-[11px] font-bold text-[#7C3AED] bg-[#EDE9FE] px-2 py-0.5 rounded-md">
                  {Math.round(semanticWeight * 100)}% Semantic
                </span>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.1"
                  value={semanticWeight}
                  onChange={(e) => handleSemanticWeightChange(e.target.value)}
                  className="w-24 accent-[#A78BFA] cursor-pointer"
                />
                <span className="text-[11px] font-bold text-[#2563EB] bg-[#EFF6FF] px-2 py-0.5 rounded-md">
                  {Math.round(keywordWeight * 100)}% Keyword
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-600">Results:</span>
                <select
                  value={topK}
                  onChange={(e) => setTopK(e.target.value)}
                  className="bg-[#F8F7FC] border border-[#E2E8F0] text-slate-700 text-xs rounded-xl px-2.5 py-1 focus:outline-none focus:border-[#A78BFA]"
                >
                  <option value={3}>Top 3</option>
                  <option value={5}>Top 5</option>
                  <option value={8}>Top 8</option>
                  <option value={10}>Top 10</option>
                </select>
              </div>
            </div>
          )}
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-[#FFF1F2] border border-[#FDA4AF] text-[#9F1239] text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-[#E11D48]" />
          <span>{error}</span>
        </div>
      )}

      {/* Results Section */}
      {results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span className="font-semibold">
              Found {results.results?.length || 0} matching excerpt{(results.results?.length || 0) === 1 ? '' : 's'}
            </span>
            <span className="font-mono text-[11px] bg-white border border-[#E2E8F0] px-2.5 py-1 rounded-lg">
              Mode: {results.search_mode || searchMode}
            </span>
          </div>

          {results.results?.length === 0 ? (
            <div className="bg-white border border-[#E2E8F0] rounded-3xl p-12 text-center space-y-2 shadow-subtle">
              <div className="w-12 h-12 rounded-2xl bg-[#F8F7FC] text-slate-400 flex items-center justify-center mx-auto">
                <Search className="w-6 h-6" />
              </div>
              <p className="text-sm font-bold text-slate-700">No matching documents</p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Try different keywords or use Hybrid Search.
              </p>
            </div>
          ) : (
            <div className="space-y-3.5">
              {results.results.map((item, index) => {
                const score = item.similarity_score ?? item.combined_score ?? item.score;
                const filename = item.filename || item.original_filename || `Document #${item.file_id}`;

                return (
                  <div
                    key={index}
                    className="bg-white border border-[#E2E8F0] rounded-3xl p-5 shadow-subtle hover:shadow-card transition space-y-3"
                  >
                    {/* Top Row: Filename, Score, Action buttons */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-8 h-8 rounded-xl bg-[#FAF8FF] border border-[#E2E8F0] flex items-center justify-center text-[#7C3AED] shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <span className="text-xs font-bold text-slate-800 truncate">
                          {filename}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {score !== undefined && score !== null && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-[#EDE9FE] text-[#7C3AED] border border-[#DDD6FE]">
                            <Award className="w-3 h-3" />
                            <span>{(score * 100).toFixed(1)}%</span>
                          </span>
                        )}

                        <button
                          onClick={() => handleView(item.file_id, filename)}
                          className="p-1.5 rounded-xl border border-[#E2E8F0] text-slate-600 hover:text-[#7C3AED] hover:border-[#A78BFA] transition text-[11px] font-semibold flex items-center gap-1"
                          title="Preview Document"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span className="hidden sm:inline">View</span>
                        </button>

                        <button
                          onClick={() => handleOpen(item.file_id)}
                          className="p-1.5 rounded-xl border border-[#E2E8F0] text-slate-600 hover:text-[#7C3AED] hover:border-[#A78BFA] transition text-[11px] font-semibold flex items-center gap-1"
                          title="Open in new tab"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span className="hidden sm:inline">Open</span>
                        </button>
                      </div>
                    </div>

                    {/* Excerpt Body */}
                    <div className="p-3.5 rounded-2xl bg-[#F8F7FC] border border-[#E2E8F0] text-xs text-slate-700 font-sans leading-relaxed selection:bg-[#EDE9FE]">
                      <p className="whitespace-pre-wrap line-clamp-4">
                        {item.chunk_text || item.text || 'No text snippet available.'}
                      </p>
                    </div>

                    {/* Metadata footer */}
                    <div className="flex items-center gap-2 text-[11px] text-slate-400">
                      {item.chunk_index !== undefined && (
                        <span>Chunk #{item.chunk_index + 1}</span>
                      )}
                    </div>
                  </div>
                );
              })}
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
          onOpenTab={(f) => handleOpen(f.id)}
        />
      )}
    </div>
  );
}
