import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, Loader2, Download, CheckCircle } from 'lucide-react';
import clsx from 'clsx';
import Badge from '@/components/Badge';
import ErrorCard from '@/components/ErrorCard';
import { getEvaluationCases, runEvaluation } from '@/lib/api';
import type { BenchmarkCase, BenchmarkReport } from '@/lib/types';

export default function Evaluation() {
  const [cases, setCases] = useState<BenchmarkCase[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [report, setReport] = useState<BenchmarkReport | null>(null);

  useEffect(() => {
    getEvaluationCases()
      .then(c => { setCases(c); setSelected(new Set(c.slice(0, 3).map(x => x.id))); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const toggle = (id: string) => {
    setSelected(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });
  };

  const run = async () => {
    setRunning(true); setError(''); setReport(null);
    try {
      const results: BenchmarkReport[] = [];
      for (const id of selected) {
        const r = await runEvaluation([id]);
        results.push(r);
      }
      if (results.length) {
        setReport({ ...results[0], cases: results.flatMap(r => r.cases) });
      }
    } catch (e: any) { setError(e?.response?.data?.detail || e?.message || 'Evaluation failed'); }
    finally { setRunning(false); }
  };

  if (loading) return <div className="space-y-4 animate-fade-in"><div className="rc-skeleton h-10 w-72" /><div className="grid grid-cols-3 gap-3">{[1,2,3].map(i=><div key={i} className="rc-skeleton h-20" />)}</div></div>;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
        <BarChart3 className="text-primary-500" /> Evaluation & Benchmarking
      </h1>
      <p className="text-sm text-muted">Compare a plain AI response with the reviewed and verified pipeline on annotated synthetic procedures.</p>

      {error && <ErrorCard message={error} />}

      {/* Test case selector */}
      <div>
        <h2 className="text-sm font-semibold mb-3">Test Cases</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {cases.map(c => (
            <button key={c.id} onClick={() => toggle(c.id)}
              className={clsx(
                'rc-card p-4 text-left transition-all duration-150 cursor-pointer',
                selected.has(c.id) ? 'border-primary-400 ring-2 ring-primary-100 bg-primary-50/50' : 'hover:border-primary-300',
              )}>
              <div className="flex items-start gap-3">
                <div className={clsx(
                  'w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors',
                  selected.has(c.id) ? 'border-primary-500 bg-primary-500' : 'border-surface-300',
                )}>
                  {selected.has(c.id) && <CheckCircle size={12} className="text-white" />}
                </div>
                <span className="text-sm font-medium">{c.title}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <p className="text-xs text-muted">This comparison uses ~{selected.size * 3} AI calls and your connected plan allowance.</p>
      <button onClick={run} disabled={!selected.size || running} className="rc-btn-primary">
        {running ? <><Loader2 size={16} className="animate-spin" /> Running comparison…</> : 'Run comparison'}
      </button>

      {/* Results */}
      {report && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          <div className="rc-card p-5">
            <p className="text-sm text-muted leading-relaxed">{report.methodology}</p>
          </div>
          <div className="rc-card border-amber-200 bg-amber-50/50 p-4 text-sm text-amber-800">{report.limitations}</div>

          {/* Results table */}
          <div className="rc-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="bg-surface-50 border-b border-surface-200">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Case</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Method</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Metric</th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Precision</th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Recall</th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">F1</th>
              </tr></thead>
              <tbody>
                {report.cases.flatMap(c =>
                  (['plain_llm', 'multipass_verified'] as const).flatMap(mode => {
                    const result = c[mode];
                    if (result.status !== 'ok' || !result.metrics) return [];
                    return Object.entries(result.metrics).map(([metric, scores]) => (
                      <tr key={`${c.title}-${mode}-${metric}`} className="border-b border-surface-100 hover:bg-surface-50 transition-colors">
                        <td className="px-4 py-2.5">{c.title}</td>
                        <td className="px-4 py-2.5">
                          <Badge variant={mode === 'multipass_verified' ? 'success' : 'default'}>
                            {mode.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5 text-muted">{metric.replace(/_/g, ' ')}</td>
                        <td className="px-4 py-2.5 text-right font-mono text-xs">{scores.precision.toFixed(3)}</td>
                        <td className="px-4 py-2.5 text-right font-mono text-xs">{scores.recall.toFixed(3)}</td>
                        <td className="px-4 py-2.5 text-right font-mono text-xs font-semibold">{scores.f1.toFixed(3)}</td>
                      </tr>
                    ));
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Error cases */}
          {report.cases.flatMap(c => (['plain_llm', 'multipass_verified'] as const).map(mode => ({ ...c[mode], title: c.title, mode }))).filter(r => r.status !== 'ok').map((r, i) => (
            <ErrorCard key={i} message={`${r.title} / ${r.mode.replace(/_/g, ' ')}: ${r.error}`} />
          ))}

          <button onClick={() => {
            const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = 'benchmark-report.json'; a.click();
            URL.revokeObjectURL(url);
          }} className="rc-btn-primary"><Download size={16} /> Download Benchmark Report</button>
        </motion.div>
      )}
    </motion.div>
  );
}
