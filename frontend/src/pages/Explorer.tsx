import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GitBranch, Plus, Save, Loader2, ChevronDown, Clock } from 'lucide-react';
import AnalysisSelector from '@/components/AnalysisSelector';
import WorkflowGraph from '@/components/WorkflowGraph';
import DetailDrawer from '@/components/DetailDrawer';
import Badge from '@/components/Badge';
import { getVersions, createVersion } from '@/lib/api';
import type { AnalysisResponse, State, Transition } from '@/lib/types';

export default function Explorer() {
  const [row, setRow] = useState<AnalysisResponse | null>(null);
  const [drawer, setDrawer] = useState<{ data: Record<string, unknown>; isEdge: boolean } | null>(null);
  const [versions, setVersions] = useState<AnalysisResponse[]>([]);
  const [showVersions, setShowVersions] = useState(false);
  const [showFindings, setShowFindings] = useState(false);
  const [editing, setEditing] = useState(false);
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (row) getVersions(row.id).then(setVersions); }, [row]);

  const a = row?.analysis;
  const names = a ? Object.fromEntries(a.process.states.map(s => [s.id, s.name])) : {};

  const handleSave = async () => {
    if (!row || !reason.trim()) return;
    setSaving(true);
    try {
      await createVersion(row.id, { reason });
      setReason(''); setEditing(false);
    } finally { setSaving(false); }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3"><GitBranch className="text-primary-500" /> Workflow Explorer</h1>
        {a && <button onClick={() => setEditing(!editing)} className="rc-btn-ghost text-xs"><Plus size={14} /> Edit workflow</button>}
      </div>
      <AnalysisSelector value={row?.id ?? null} onChange={(_, r) => setRow(r)} />

      {a && (
        <>
          <WorkflowGraph process={a.process}
            onNodeClick={(s: State) => setDrawer({ data: s as any, isEdge: false })}
            onEdgeClick={(t: Transition) => setDrawer({ data: t as any, isEdge: true })} />

          {/* Edit panel */}
          <AnimatePresence>
            {editing && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="rc-card p-5 space-y-4 overflow-hidden">
                <h3 className="text-sm font-semibold">Save a New Version</h3>
                <p className="text-xs text-muted">Saving creates a new version. Edited elements are marked as user revisions.</p>
                <input value={reason} onChange={e => setReason(e.target.value)} placeholder="Reason for this version…" className="rc-input" />
                <button onClick={handleSave} disabled={!reason.trim() || saving} className="rc-btn-primary text-xs">
                  {saving ? <><Loader2 size={14} className="animate-spin" /> Saving…</> : <><Save size={14} /> Save as new version</>}
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Findings */}
          <button onClick={() => setShowFindings(!showFindings)} className="rc-btn-ghost text-xs w-full justify-between">
            Findings ({a.findings.length}) <ChevronDown size={14} className={`transition-transform ${showFindings ? 'rotate-180' : ''}`} />
          </button>
          <AnimatePresence>
            {showFindings && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="space-y-2 overflow-hidden">
                {a.findings.map((f, i) => (
                  <div key={i} className="rc-card p-3 flex items-start gap-3">
                    <Badge variant={f.severity}>{f.severity.toUpperCase()}</Badge>
                    <p className="text-sm text-ink">{f.message}</p>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Version history */}
          <button onClick={() => setShowVersions(!showVersions)} className="rc-btn-ghost text-xs w-full justify-between">
            Version History ({versions.length}) <ChevronDown size={14} className={`transition-transform ${showVersions ? 'rotate-180' : ''}`} />
          </button>
          <AnimatePresence>
            {showVersions && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="relative pl-6 space-y-4 border-l-2 border-surface-300 ml-3">
                  {versions.map((v, i) => (
                    <div key={v.id} className="relative">
                      <div className="absolute -left-[25px] w-3 h-3 rounded-full border-2 border-primary-400 bg-white" />
                      <div className="rc-card p-3">
                        <div className="flex items-center gap-2 text-xs text-muted"><Clock size={12} />{v.created_at.slice(0, 19).replace('T', ' ')}</div>
                        <p className="text-sm mt-1">{v.analysis.revision_reason || (i === versions.length - 1 ? 'Original analysis' : 'Revision')}</p>
                        <p className="text-xs text-muted mt-1">{(v.analysis.stages || []).join(' → ') || 'Legacy single-pass'}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}

      <DetailDrawer open={!!drawer} onClose={() => setDrawer(null)} data={drawer?.data ?? null} isEdge={drawer?.isEdge} names={names} sentences={a?.sentences} />
    </motion.div>
  );
}
