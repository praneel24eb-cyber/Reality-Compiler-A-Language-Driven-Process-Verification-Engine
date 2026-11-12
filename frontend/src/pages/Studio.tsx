import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Upload, FileText, Beaker, Loader2, Check, AlertTriangle } from 'lucide-react';
import { createAnalysis, extractPdfText } from '@/lib/api';

export default function Studio() {
  const [source, setSource] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: 'success' | 'warning'; message: string } | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (file.size > 10_000_000) { setResult({ type: 'warning', message: 'File exceeds 10 MB.' }); return; }
    if (file.name.toLowerCase().endsWith('.txt')) {
      const text = await file.text();
      if (text.length > 200000) { setResult({ type: 'warning', message: 'Text exceeds 200,000 character limit.' }); return; }
      setSource(text);
    } else if (file.name.toLowerCase().endsWith('.pdf')) {
      try {
        const extracted = await extractPdfText(file);
        setSource(extracted.source);
        setResult({ type: 'success', message: `Text extracted from ${extracted.page_count} PDF pages. Review it below, then select Analyze and save.` });
      } catch (e: any) {
        setResult({ type: 'warning', message: e?.response?.data?.detail || e?.message || 'Could not read this PDF.' });
      }
    } else {
      setResult({ type: 'warning', message: 'Choose a PDF or UTF-8 text file.' });
    }
  };

  const analyze = async () => {
    setLoading(true); setResult(null);
    try {
      const saved = await createAnalysis(source);
      const p = saved.analysis.process;
      if (!p.transitions.length) setResult({ type: 'warning', message: 'Saved for review, but no transitions extracted. Cover pages may not describe a procedure.' });
      else setResult({ type: 'success', message: `Saved ${p.states.length} steps and ${p.transitions.length} transitions. Open Workflow Explorer to explore.` });
    } catch (e: any) {
      setResult({ type: 'warning', message: e?.response?.data?.detail || e?.message || 'Analysis failed' });
    } finally { setLoading(false); }
  };

  const pct = Math.min(100, (source.length / 200000) * 100);

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 max-w-3xl">
      <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
        <Upload className="text-primary-500" /> SOP Input Studio
      </h1>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); }}
        onClick={() => fileRef.current?.click()}
        className={`rc-card border-2 border-dashed p-10 text-center cursor-pointer transition-all duration-200 ${dragOver ? 'border-primary-400 bg-primary-50' : 'border-surface-300 hover:border-primary-300 hover:bg-surface-50'}`}
      >
        <FileText size={36} className="mx-auto text-primary-400 mb-3" />
        <p className="text-sm font-medium text-ink">Drop a PDF or UTF-8 text file here</p>
        <p className="text-xs text-muted mt-1">or click to browse</p>
        <input ref={fileRef} type="file" accept=".pdf,.txt" hidden onChange={e => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} />
      </div>

      {/* Synthetic sample */}
      <button className="rc-btn-ghost text-xs" onClick={() => setSource('The clerk receives a request. The manager reviews it. The clerk archives it.')}>
        <Beaker size={14} /> Use synthetic sample
      </button>

      {/* Editor */}
      <div className="space-y-2">
        <textarea value={source} onChange={e => setSource(e.target.value)} maxLength={200000} placeholder="Paste or type your SOP here…"
          className="rc-input min-h-[200px] resize-y font-mono text-xs" />
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted">{source.length.toLocaleString()} / 200,000 characters</span>
          <div className="w-48 h-1.5 bg-surface-200 rounded-full overflow-hidden">
            <div className={`h-full rounded-full transition-all duration-300 ${pct > 90 ? 'bg-red-400' : pct > 70 ? 'bg-amber-400' : 'bg-primary-400'}`} style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>

      {/* Actions */}
      <button onClick={analyze} disabled={!source.trim() || loading} className="rc-btn-primary">
        {loading ? <><Loader2 size={16} className="animate-spin" /> Analyzing…</> : 'Analyze and save'}
      </button>

      {/* Result */}
      {result && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className={`rc-card p-4 flex items-start gap-3 ${result.type === 'success' ? 'border-green-200 bg-green-50/50' : 'border-amber-200 bg-amber-50/50'}`}>
          {result.type === 'success' ? <Check size={18} className="text-green-600 mt-0.5" /> : <AlertTriangle size={18} className="text-amber-500 mt-0.5" />}
          <p className="text-sm">{result.message}</p>
        </motion.div>
      )}
    </motion.div>
  );
}
