import React, { useState } from 'react';
import api from '../api/client';
import { 
  Bot, 
  Send, 
  Sparkles, 
  Quote, 
  FileText, 
  Layers, 
  AlertCircle, 
  Loader2, 
  CheckCircle2, 
  HelpCircle,
  Cpu
} from 'lucide-react';

export default function RagPage() {
  const [question, setQuestion] = useState('');
  const [topK, setTopK] = useState(5);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
      const res = await api.post('/rag/ask', {
        question: question.trim(),
        top_k: Number(topK),
      });
      setResponse(res.data);
    } catch (err) {
      setError(err.message || 'RAG generation failed. Please ensure Ollama is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-2">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Grounded Retrieval-Augmented Generation</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Ask AI (RAG)</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Query your document repository using natural language. Answers are strictly grounded in retrieved chunks with citations.
        </p>
      </div>

      {/* Query Form */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm space-y-4">
        <form onSubmit={handleAsk} className="space-y-3">
          <div className="relative">
            <textarea
              rows={3}
              required
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your uploaded documents..."
              className="w-full p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition resize-none"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>Context Chunks (top_k):</span>
              <select
                value={topK}
                onChange={(e) => setTopK(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-2.5 py-1 focus:outline-none focus:border-brand-500"
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
              className="py-2.5 px-5 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-brand-600/20 flex items-center gap-2 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Synthesizing Answer...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Generate Grounded Answer</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Sample Question Chips */}
        {!response && !loading && (
          <div className="pt-3 border-t border-slate-800/80">
            <span className="text-[11px] text-slate-500 block mb-2 font-medium">Try an example question:</span>
            <div className="flex flex-wrap gap-2">
              {sampleQuestions.map((sq, i) => (
                <button
                  key={i}
                  onClick={() => setQuestion(sq)}
                  className="text-left text-[11px] text-slate-400 hover:text-slate-200 bg-slate-950/60 hover:bg-slate-800/50 border border-slate-800 px-3 py-1.5 rounded-lg transition"
                >
                  "{sq}"
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Answer & Citations Card */}
      {response && (
        <div className="space-y-6">
          {/* Answer Card */}
          <div className="bg-slate-900/90 border border-emerald-500/30 rounded-2xl p-6 shadow-xl backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <Bot className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-white">AI Grounded Response</h2>
                  <p className="text-[11px] text-slate-500">Synthesized using Ollama Llama 3.2 3B</p>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Strict Grounding
              </span>
            </div>

            {/* Answer Content */}
            <div className="text-xs sm:text-sm text-slate-200 leading-relaxed whitespace-pre-wrap selection:bg-emerald-500/30 font-sans">
              {response.answer}
            </div>
          </div>

          {/* Citations Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Quote className="w-4 h-4 text-brand-400" />
                <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Source Citations ({response.citations?.length || 0})
                </h3>
              </div>
              <span className="text-[11px] text-slate-500">
                Direct evidence used by the model
              </span>
            </div>

            {response.citations && response.citations.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {response.citations.map((c, i) => (
                  <div
                    key={i}
                    className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 truncate">
                        <FileText className="w-3.5 h-3.5 text-brand-400 shrink-0" />
                        <span className="text-xs font-semibold text-slate-200 truncate">
                          {c.original_filename}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded shrink-0">
                        sim: {typeof c.similarity_score === 'number' ? c.similarity_score.toFixed(3) : c.similarity_score}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-400 font-mono line-clamp-3 bg-slate-900/60 p-2 rounded-lg border border-slate-800/50">
                      "{c.snippet}"
                    </p>

                    <div className="flex items-center gap-1 text-[10px] text-slate-500">
                      <Layers className="w-3 h-3" />
                      <span>Chunk #{c.chunk_index} (File ID #{c.file_id})</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No citations were returned for this answer.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
