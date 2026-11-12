import { useState } from 'react';
import { motion } from 'framer-motion';
import { FlaskConical, Loader2, ArrowRight, Plus, Minus, Edit3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AnalysisSelector from '@/components/AnalysisSelector';
import WorkflowGraph from '@/components/WorkflowGraph';
import Badge from '@/components/Badge';
import { createScenario } from '@/lib/api';
import type { AnalysisResponse, ScenarioResult } from '@/lib/types';

export default function Simulation() {
  const [row, setRow] = useState<AnalysisResponse | null>(null);
  const [operation, setOperation] = useState('remove_transition');
  const [elementId, setElementId] = useState('');
  const [field, setField] = useState('label');
  const [newValue, setNewValue] = useState('');
  const [removeCondition, setRemoveCondition] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const nav = useNavigate();

  const a = row?.analysis;
  const names = a ? Object.fromEntries(a.process.states.map(s => [s.id, s.name])) : {};
  const ops = a ? [
    ...(a.process.transitions.length ? ['remove_transition', 'change_transition'] : []),
    ...(a.process.states.length ? ['remove_state'] : []),
  ] : [];
  const collection = operation === 'remove_state' ? a?.process.states : a?.process.transitions;

  const run = async () => {
    if (!row || !elementId) return;
    setLoading(true);
    try {
      const payload: Record<string, unknown> = { operation, element_id: elementId };
      if (operation === 'change_transition') payload[field] = removeCondition && field === 'condition' ? null : newValue;
      const r = await createScenario(row.id, payload);
      setResult(r);
    } catch {} finally { setLoading(false); }
  };

  const opIcons = { remove_transition: <Minus size={14} />, change_transition: <Edit3 size={14} />, remove_state: <Minus size={14} /> };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3"><FlaskConical className="text-primary-500" /> What-If Simulation Lab</h1>
      <p className="text-sm text-muted">Scenarios are saved separately; the original is never overwritten.</p>
      <AnalysisSelector value={row?.id ?? null} onChange={(_, r) => { setRow(r); setResult(null); }} />

      {a && (
        <>
          <p className="text-xs text-muted">{a.process.states.length} steps · {a.process.transitions.length} transitions</p>
          {!a.process.transitions.length && (
            <div className="rc-card border-amber-200 bg-amber-50/50 p-4 text-sm text-amber-800">
              No transitions to simulate. <button onClick={() => nav('/studio')} className="underline font-medium">Open SOP Input Studio</button>
            </div>
          )}
          {ops.length > 0 && (
            <div className="rc-card p-5 space-y-4">
              {/* Operation selector */}
              <div className="flex gap-2">
                {ops.map(op => (
                  <button key={op} onClick={() => { setOperation(op); setElementId(''); }}
                    className={`rc-btn text-xs ${operation === op ? 'bg-primary-500 text-white border-primary-500' : 'bg-white text-ink border-surface-300 hover:border-primary-400'}`}>
                    {opIcons[op as keyof typeof opIcons]} {op.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())}
                  </button>
                ))}
              </div>
              {/* Element selector */}
              <select value={elementId} onChange={e => setElementId(e.target.value)} className="rc-input">
                <option value="">Select element…</option>
                {(collection || []).map((item: any) => (
                  <option key={item.id} value={item.id}>
                    {'source' in item ? `${names[item.source] || item.source} → ${names[item.target] || item.target}` : item.name}
                  </option>
                ))}
              </select>
              {operation === 'change_transition' && (
                <div className="space-y-3">
                  <select value={field} onChange={e => setField(e.target.value)} className="rc-input"><option value="label">Label</option><option value="condition">Condition</option></select>
                  <input value={newValue} onChange={e => setNewValue(e.target.value)} placeholder="New value" className="rc-input" />
                  {field === 'condition' && <label className="flex items-center gap-2 text-xs text-muted"><input type="checkbox" checked={removeCondition} onChange={e => setRemoveCondition(e.target.checked)} className="rounded" /> Remove condition</label>}
                </div>
              )}
              <button onClick={run} disabled={!elementId || loading} className="rc-btn-primary text-xs">
                {loading ? <><Loader2 size={14} className="animate-spin" /> Running…</> : 'Run scenario'}
              </button>
            </div>
          )}

          {/* Results */}
          {result && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <div><h3 className="text-sm font-semibold mb-2">Original</h3><WorkflowGraph process={a.process} /></div>
                <div><h3 className="text-sm font-semibold mb-2">Scenario</h3><WorkflowGraph process={result.process} /></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {([['New Findings', result.new_findings, 'error'],['Resolved', result.resolved_findings, 'success'],['Lost Reachability', result.lost_reachability, 'warning'],['Gained Reachability', result.gained_reachability, 'info']] as const).map(([title, items, variant]) => (
                  <div key={title} className="rc-card p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-muted">{title}</span>
                      <Badge variant={variant as string}>{items.length}</Badge>
                    </div>
                    {items.length ? items.map((item: any, i: number) => (
                      <p key={i} className="text-xs text-ink mt-1">{typeof item === 'string' ? (names[item] || item) : item.message}</p>
                    )) : <p className="text-xs text-muted italic">None</p>}
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </>
      )}
    </motion.div>
  );
}
