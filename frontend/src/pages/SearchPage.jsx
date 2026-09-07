import React, { useState } from 'react';
import api from '../api/client';
import { 
  Search, 
  Sparkles, 
  Key, 
  SlidersHorizontal, 
  FileText, 
  Layers, 
  AlertCircle, 
  Loader2, 
  Info,
  Calendar
} from 'lucide-react';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState('hybrid'); // 'hybrid', 'semantic', 'keyword'
  const [topK, setTopK] = useState(5);
  const [semanticWeight, setSemanticWeight] = useState(0.6);
  const [keywordWeight, setKeywordWeight] = useState(0.4);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      let endpoint = '/search/hybrid';
      let payload = {
        query: query.trim(),
        top_k: Number(topK),
      };

      if (searchMode === 'semantic') {
        endpoint = '/search/semantic';
      } else if (searchMode === 'keyword') {
        endpoint = '/search/keyword';
      } else {
        // Hybrid
        payload.semantic_weight = Number(semanticWeight);
        payload.keyword_weight = Number(keywordWeight);
      }

      const res = await api.post(endpoint, payload);
      setResults(res.data);
    } catch (err) {
      setError(err.message || 'Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSemanticWeightChange = (val) => {
    const sw = parseFloat(val);
    setSemanticWeight(sw);
    setKeywordWeight(parseFloat((1.0 - sw).toFixed(2)));
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Intelligent Search Engine</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Perform multi-modal search combining dense vector embeddings and sparse full-text keyword retrieval.
        </p>
      </div>

      {/* Mode Tabs */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 bg-slate-900/90 border border-slate-800 rounded-2xl w-fit">
        <button
          onClick={() => setSearchMode('hybrid')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            searchMode === 'hybrid'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/20'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Hybrid Search</span>
        </button>

        <button
          onClick={() => setSearchMode('semantic')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            searchMode === 'semantic'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/20'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Semantic Search</span>
        </button>

        <button
          onClick={() => setSearchMode('keyword')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            searchMode === 'keyword'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/20'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Key className="w-3.5 h-3.5" />
          <span>Keyword Search</span>
        </button>
      </div>

      {/* Search Input Box */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm space-y-4">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
              <Search className="w-5 h-5" />
            </div>
            <input
              type="text"
              required
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                searchMode === 'semantic'
                  ? 'Ask or describe concepts in plain English (e.g. "financial revenue growth metrics")...'
                  : searchMode === 'keyword'
                  ? 'Search specific words or phrases (e.g. "invoice 2024 total")...'
                  : 'Enter a search query to combine semantic concepts and exact terms...'
              }
              className="w-full pl-11 pr-28 py-3.5 bg-slate-950/80 border border-slate-800 rounded-xl text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition"
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-2 top-2 bottom-2 px-5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-md transition flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>Search</span>
                </>
              )}
            </button>
          </div>

          {/* Search Configuration Filters */}
          <div className="pt-2 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="text-slate-400 font-medium block mb-1">
                Results Count (top_k): <span className="text-slate-200 font-semibold">{topK}</span>
              </label>
              <input
                type="range"
                min="1"
                max="20"
                value={topK}
                onChange={(e) => setTopK(e.target.value)}
                className="w-full accent-brand-500 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>

            {searchMode === 'hybrid' && (
              <>
                <div>
                  <label className="text-slate-400 font-medium block mb-1">
                    Semantic Weight: <span className="text-brand-400 font-semibold">{semanticWeight}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={semanticWeight}
                    onChange={(e) => handleSemanticWeightChange(e.target.value)}
                    className="w-full accent-brand-500 bg-slate-800 rounded-lg cursor-pointer"
                  />
                </div>

                <div>
                  <label className="text-slate-400 font-medium block mb-1">
                    Keyword Weight: <span className="text-indigo-400 font-semibold">{keywordWeight}</span>
                  </label>
                  <div className="h-4 flex items-center">
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-indigo-500 h-full rounded-full transition-all"
                        style={{ width: `${keywordWeight * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Results Section */}
      {results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span>
              Found <strong className="text-white">{results.total_results}</strong> relevant chunks for "{results.query}"
            </span>
            <span className="uppercase text-[11px] font-mono bg-slate-900 px-2.5 py-0.5 rounded-full border border-slate-800 text-slate-300">
              Mode: {results.search_mode}
            </span>
          </div>

          {results.results.length === 0 ? (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-12 text-center text-xs text-slate-400 space-y-2">
              <Info className="w-6 h-6 mx-auto text-slate-500" />
              <p className="font-semibold text-slate-300">No matching chunks found</p>
              <p className="text-slate-500">Try rephrasing your query or adjusting the search weights.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {results.results.map((item, idx) => (
                <div
                  key={item.chunk_id || idx}
                  className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 transition backdrop-blur-sm space-y-3"
                >
                  {/* Result Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <FileText className="w-4 h-4 text-brand-400 shrink-0" />
                      <span className="text-xs font-semibold text-slate-200 truncate max-w-xs sm:max-w-md">
                        {item.original_filename}
                      </span>
                      {item.extension && (
                        <span className="text-[10px] font-mono uppercase bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 text-slate-400">
                          {item.extension.replace('.', '')}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-400">Score:</span>
                      <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                        {typeof item.similarity_score === 'number'
                          ? item.similarity_score.toFixed(4)
                          : item.similarity_score}
                      </span>
                    </div>
                  </div>

                  {/* Chunk Text Snippet */}
                  <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3.5 text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">
                    {item.chunk_text}
                  </div>

                  {/* Sub-scores and Metadata */}
                  <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 pt-1">
                    <span className="flex items-center gap-1">
                      <Layers className="w-3 h-3 text-slate-400" />
                      Chunk #{item.chunk_index} (ID: {item.chunk_id})
                    </span>
                    {item.semantic_score !== null && item.semantic_score !== undefined && (
                      <span>Semantic: <strong className="text-slate-400">{item.semantic_score.toFixed(3)}</strong></span>
                    )}
                    {item.keyword_score !== null && item.keyword_score !== undefined && (
                      <span>Keyword: <strong className="text-slate-400">{item.keyword_score.toFixed(3)}</strong></span>
                    )}
                    {item.uploaded_at && (
                      <span className="flex items-center gap-1 ml-auto">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        {new Date(item.uploaded_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
