import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ChevronDown, User } from 'lucide-react';
import AnalysisSelector from '@/components/AnalysisSelector';
import DetailDrawer from '@/components/DetailDrawer';
import Badge from '@/components/Badge';
import type { AnalysisResponse } from '@/lib/types';

export default function Inspector() {
  const [row, setRow] = useState<AnalysisResponse | null>(null);
  const [drawer, setDrawer] = useState<{ data: Record<string, unknown>; isEdge: boolean } | null>(null);
  const [showPassages, setShowPassages] = useState(false);

  const a = row?.analysis;
  const names = a ? Object.fromEntries(a.process.states.map(s => [s.id, s.name])) : {};

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
        <Search className="text-primary-500" /> Extraction Inspector
      </h1>
      <AnalysisSelector value={row?.id ?? null} onChange={(_, r) => setRow(r)} />

      {a && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
          {/* Source passages */}
          <button onClick={() => setShowPassages(!showPassages)} className="rc-btn-ghost text-xs w-full justify-between">
            Source passages ({a.sentences.length}) <ChevronDown size={14} className={`transition-transform ${showPassages ? 'rotate-180' : ''}`} />
          </button>
          <AnimatePresence>
            {showPassages && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                className="rc-card p-4 space-y-2 overflow-hidden">
                {a.sentences.map(s => (
                  <div key={s.id} className="text-xs text-ink leading-relaxed">
                    {s.text}
                    {s.start != null && <span className="text-[10px] text-muted ml-2">chars {s.start}–{s.end}</span>}
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Actors */}
          <div>
            <h2 className="text-sm font-semibold mb-2">People and Teams</h2>
            <div className="flex flex-wrap gap-2">
              {a.process.actors.length ? a.process.actors.map(actor => (
                <span key={actor} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary-50 text-primary-700 text-xs font-medium border border-primary-200">
                  <User size={12} /> {actor}
                </span>
              )) : <span className="text-sm text-muted italic">Not stated</span>}
            </div>
          </div>

          {/* Steps table */}
          <div>
            <h2 className="text-sm font-semibold mb-2">Workflow Steps</h2>
            <div className="rc-card overflow-hidden">
              <table className="w-full text-sm">
                <thead><tr className="bg-surface-50 border-b border-surface-200">
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Step</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Type</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Actor</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Inferred</th>
                </tr></thead>
                <tbody>
                  {a.process.states.map((s, i) => (
                    <tr key={s.id} onClick={() => setDrawer({ data: s as any, isEdge: false })}
                      className={`border-b border-surface-100 cursor-pointer hover:bg-surface-50 transition-colors ${i % 2 ? 'bg-surface-50/50' : ''}`}>
                      <td className="px-4 py-2.5 font-medium">{s.name}</td>
                      <td className="px-4 py-2.5"><Badge variant={s.kind}>{s.kind.toUpperCase()}</Badge></td>
                      <td className="px-4 py-2.5 text-muted">{s.actor || 'Not stated'}</td>
                      <td className="px-4 py-2.5"><Badge variant={s.inferred ? 'yes' : 'no'}>{s.inferred ? 'Yes' : 'No'}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Transitions table */}
          <div>
            <h2 className="text-sm font-semibold mb-2">Transitions</h2>
            <div className="rc-card overflow-hidden">
              <table className="w-full text-sm">
                <thead><tr className="bg-surface-50 border-b border-surface-200">
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">From</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">To</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Condition</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted uppercase tracking-wider">Actor</th>
                </tr></thead>
                <tbody>
                  {a.process.transitions.map((t, i) => (
                    <tr key={t.id} onClick={() => setDrawer({ data: t as any, isEdge: true })}
                      className={`border-b border-surface-100 cursor-pointer hover:bg-surface-50 transition-colors ${i % 2 ? 'bg-surface-50/50' : ''}`}>
                      <td className="px-4 py-2.5">{names[t.source] || t.source}</td>
                      <td className="px-4 py-2.5">{names[t.target] || t.target}</td>
                      <td className="px-4 py-2.5 text-muted">{t.condition || t.label || '—'}</td>
                      <td className="px-4 py-2.5 text-muted">{t.actor || 'Not stated'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      )}

      <DetailDrawer open={!!drawer} onClose={() => setDrawer(null)} data={drawer?.data ?? null} isEdge={drawer?.isEdge} names={names} sentences={a?.sentences} />
    </motion.div>
  );
}
