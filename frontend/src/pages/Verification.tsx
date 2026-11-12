import { useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Quote, ArrowRight } from 'lucide-react';
import AnalysisSelector from '@/components/AnalysisSelector';
import Badge from '@/components/Badge';
import type { AnalysisResponse } from '@/lib/types';

export default function Verification() {
  const [row, setRow] = useState<AnalysisResponse | null>(null);
  const a = row?.analysis;
  const names = a ? Object.fromEntries(a.process.states.map(s => [s.id, s.name])) : {};

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
        <ShieldCheck className="text-primary-500" /> Verification Center
      </h1>
      <AnalysisSelector value={row?.id ?? null} onChange={(_, r) => setRow(r)} />

      {a && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
          {/* Rules */}
          {a.rules.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold mb-3">Required-Step Rules</h2>
              <div className="space-y-2">
                {a.rules.map((rule, i) => (
                  <div key={i} className="rc-card p-4 flex items-center gap-3">
                    <ShieldCheck size={16} className="text-primary-500 flex-shrink-0" />
                    <p className="text-sm">
                      <strong>{names[rule.protected] || rule.protected}</strong> must occur before{' '}
                      <strong>{rule.target ? (names[rule.target] || rule.target) : 'every terminal outcome'}</strong>
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Findings by severity */}
          {(['error', 'warning', 'info'] as const).map(severity => {
            const items = a.findings.filter(f => f.severity === severity);
            if (!items.length) return null;
            return (
              <div key={severity}>
                <h2 className="text-sm font-semibold mb-3 capitalize">{severity}s ({items.length})</h2>
                <div className="space-y-3">
                  {items.map((f, i) => {
                    const ledger = Object.fromEntries(a.sentences.map(s => [s.id, s.text]));
                    return (
                      <div key={i} className="rc-card p-4 space-y-3">
                        <div className="flex items-start gap-3">
                          <Badge variant={f.severity}>{f.severity.toUpperCase()}</Badge>
                          <div className="flex-1">
                            <p className="text-sm font-medium">{f.type.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())}</p>
                            <p className="text-sm text-muted mt-0.5">{f.message}</p>
                          </div>
                        </div>
                        <p className="text-[10px] text-muted uppercase tracking-wider font-medium">
                          {f.method === 'llm_review' ? '🤖 AI source review — confirm against the procedure' : '⚙️ Deterministic structural check'}
                        </p>
                        {(f.evidence || []).map((ref, j) => (
                          <blockquote key={j} className="text-xs text-primary-800 bg-primary-50 border-l-2 border-primary-300 rounded-r-lg px-3 py-2 leading-relaxed">
                            <Quote size={10} className="inline mr-1 text-primary-400" />
                            {ledger[ref] || 'Source passage unavailable'}
                          </blockquote>
                        ))}
                        {f.counterexample_path && (
                          <div className="flex items-center gap-2 flex-wrap text-xs">
                            <span className="font-medium text-muted">Path:</span>
                            {f.counterexample_path.map((step, k) => (
                              <span key={k} className="flex items-center gap-1">
                                <span className="px-2 py-0.5 rounded bg-surface-200 text-ink font-medium">{names[step] || step}</span>
                                {k < f.counterexample_path!.length - 1 && <ArrowRight size={12} className="text-muted" />}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </motion.div>
      )}
    </motion.div>
  );
}
